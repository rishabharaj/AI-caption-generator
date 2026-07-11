"""
CapturaAI — Fine-tuning pipeline for video captioning models.

Supports MSR-VTT and ActivityNet datasets with two training modes:
1. Audio+Visual: Uses transcript + visual frames
2. Visual-Only: Uses only visual frames (for mute videos)

Config-driven with `use_fine_tuned` toggle in config.yaml.
Proper CLI interface with argparse.

Usage:
    python -m backend.train_captioner --dataset msrvtt --mode audio_visual --epochs 3
    python -m backend.train_captioner --dataset activitynet --mode visual_only --output ./models
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class TrainingConfig:
    """Configuration for the fine-tuning pipeline."""
    dataset: str = "msrvtt"
    mode: str = "audio_visual"  # "audio_visual" or "visual_only"
    base_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"
    output_dir: str = "./fine_tuned_models"
    epochs: int = 3
    batch_size: int = 8
    learning_rate: float = 2e-5
    max_length: int = 512
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    warmup_steps: int = 100
    weight_decay: float = 0.01
    gradient_accumulation_steps: int = 4
    fp16: bool = True
    seed: int = 42
    eval_split: float = 0.1
    log_steps: int = 50
    save_steps: int = 500
    caption_styles: list[str] = field(
        default_factory=lambda: ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
    )


# ---------------------------------------------------------------------------
# Dataset Loaders
# ---------------------------------------------------------------------------

class DatasetLoader:
    """Base class for video-caption dataset loaders."""

    def __init__(self, data_dir: str, mode: str = "audio_visual"):
        """
        Initialize the dataset loader.

        Args:
            data_dir: Path to the dataset directory.
            mode: Training mode ('audio_visual' or 'visual_only').
        """
        self.data_dir = Path(data_dir)
        self.mode = mode

    def load(self) -> list[dict[str, Any]]:
        """
        Load the dataset and return a list of training samples.

        Returns:
            List of dictionaries with keys:
            - video_id: str
            - transcript: str (empty if visual_only)
            - visual_frames: list[str]
            - captions: dict[str, str] (style -> caption)
        """
        raise NotImplementedError

    def _validate_data_dir(self) -> None:
        """Validate that the data directory exists."""
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found: {self.data_dir}")


class MSRVTTLoader(DatasetLoader):
    """
    Loader for the MSR-VTT dataset.

    MSR-VTT contains 10,000 video clips with 200,000 clip-sentence pairs.
    Expected structure:
        msrvtt/
        ├── train_val_videodatainfo.json
        ├── videos/
        │   ├── video0.mp4
        │   └── ...
        └── frames/  (pre-extracted)
    """

    def load(self) -> list[dict[str, Any]]:
        """Load MSR-VTT dataset."""
        self._validate_data_dir()

        annotation_file = self.data_dir / "train_val_videodatainfo.json"
        if not annotation_file.exists():
            logger.warning(
                "MSR-VTT annotation file not found at %s. "
                "Generating sample training data.",
                annotation_file,
            )
            return self._generate_sample_data(count=100)

        logger.info("Loading MSR-VTT annotations from %s", annotation_file)
        with open(annotation_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = []
        videos = {v["video_id"]: v for v in data.get("videos", [])}
        sentences = data.get("sentences", [])

        # Group sentences by video
        from collections import defaultdict
        video_captions: dict[str, list[str]] = defaultdict(list)
        for sent in sentences:
            vid = sent.get("video_id", "")
            caption = sent.get("caption", "")
            if vid and caption:
                video_captions[vid].append(caption)

        for vid_id, captions in video_captions.items():
            if not captions:
                continue

            video_info = videos.get(vid_id, {})
            transcript = ""
            if self.mode == "audio_visual" and len(captions) > 0:
                # Use first caption as pseudo-transcript
                transcript = captions[0]

            frame_paths = self._get_frame_paths(vid_id)

            # Generate style-specific captions from available captions
            style_captions = self._distribute_captions(captions)

            samples.append({
                "video_id": vid_id,
                "transcript": transcript,
                "visual_frames": [str(f) for f in frame_paths],
                "captions": style_captions,
            })

        logger.info("Loaded %d samples from MSR-VTT", len(samples))
        return samples

    def _get_frame_paths(self, video_id: str) -> list[Path]:
        """Get pre-extracted frame paths for a video."""
        frames_dir = self.data_dir / "frames" / video_id
        if frames_dir.exists():
            return sorted(frames_dir.glob("*.jpg"))[:10]
        return []

    def _distribute_captions(self, captions: list[str]) -> dict[str, str]:
        """Distribute available captions across the 4 styles."""
        styles = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
        result: dict[str, str] = {}
        for i, style in enumerate(styles):
            idx = i % len(captions)
            result[style] = captions[idx]
        return result

    def _generate_sample_data(self, count: int = 100) -> list[dict[str, Any]]:
        """Generate sample training data for testing the pipeline."""
        samples = []
        for i in range(count):
            samples.append({
                "video_id": f"video{i}",
                "transcript": f"Sample transcript for video {i}. A person is performing an activity.",
                "visual_frames": [],
                "captions": {
                    "formal": f"This footage presents a methodical demonstration of activity {i}.",
                    "sarcastic": f"Oh joy, yet another thrilling display of activity {i}. Riveting.",
                    "humorous_tech": f"When your CI/CD pipeline for activity {i} finally passes all tests.",
                    "humorous_non_tech": f"Me trying to do activity {i} vs. how I think I look doing it.",
                },
            })
        return samples


class ActivityNetLoader(DatasetLoader):
    """
    Loader for the ActivityNet Captions dataset.

    ActivityNet contains ~20K YouTube videos with dense temporal annotations.
    Expected structure:
        activitynet/
        ├── train.json
        ├── val.json
        ├── videos/
        └── frames/
    """

    def load(self) -> list[dict[str, Any]]:
        """Load ActivityNet Captions dataset."""
        self._validate_data_dir()

        train_file = self.data_dir / "train.json"
        if not train_file.exists():
            logger.warning(
                "ActivityNet annotation file not found at %s. "
                "Generating sample training data.",
                train_file,
            )
            return MSRVTTLoader(str(self.data_dir), self.mode)._generate_sample_data(100)

        logger.info("Loading ActivityNet annotations from %s", train_file)
        with open(train_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = []
        for vid_id, info in data.items():
            sentences = info.get("sentences", [])
            timestamps = info.get("timestamps", [])

            if not sentences:
                continue

            transcript = " ".join(sentences) if self.mode == "audio_visual" else ""
            frame_paths = self._get_frame_paths(vid_id)

            # Use sentences as style variants
            style_captions: dict[str, str] = {}
            styles = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
            for i, style in enumerate(styles):
                idx = i % len(sentences)
                style_captions[style] = sentences[idx]

            samples.append({
                "video_id": vid_id,
                "transcript": transcript,
                "visual_frames": [str(f) for f in frame_paths],
                "captions": style_captions,
            })

        logger.info("Loaded %d samples from ActivityNet", len(samples))
        return samples

    def _get_frame_paths(self, video_id: str) -> list[Path]:
        """Get pre-extracted frame paths for a video."""
        frames_dir = self.data_dir / "frames" / video_id
        if frames_dir.exists():
            return sorted(frames_dir.glob("*.jpg"))[:10]
        return []


# ---------------------------------------------------------------------------
# Training Pipeline
# ---------------------------------------------------------------------------

class TrainingPipeline:
    """
    Fine-tuning pipeline for video caption models.

    Supports LoRA fine-tuning using Hugging Face Transformers + PEFT.
    """

    def __init__(self, config: TrainingConfig):
        """
        Initialize the training pipeline.

        Args:
            config: Training configuration.
        """
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_dataset(self, samples: list[dict[str, Any]]) -> list[dict[str, str]]:
        """
        Prepare training samples into prompt-completion pairs.

        Each sample becomes 4 training examples (one per style).

        Args:
            samples: Raw dataset samples.

        Returns:
            List of {"prompt": ..., "completion": ...} dictionaries.
        """
        training_data: list[dict[str, str]] = []

        from backend.services.fireworks_client import SYSTEM_PROMPTS

        for sample in samples:
            transcript = sample.get("transcript", "")
            visual_frames = sample.get("visual_frames", [])
            captions = sample.get("captions", {})

            # Build visual context string
            visual_context = f"Frames: {len(visual_frames)} frames extracted"

            for style, caption_text in captions.items():
                if style not in SYSTEM_PROMPTS:
                    continue

                system_prompt = SYSTEM_PROMPTS[style]

                if self.config.mode == "visual_only":
                    user_content = (
                        f"Visual context: {visual_context}\n"
                        f"Write a caption for this video."
                    )
                else:
                    user_content = (
                        f"Video transcript: {transcript}\n"
                        f"Visual context: {visual_context}\n"
                        f"Write a caption for this video."
                    )

                prompt = f"<|system|>{system_prompt}<|user|>{user_content}<|assistant|>"

                training_data.append({
                    "prompt": prompt,
                    "completion": caption_text,
                })

        logger.info(
            "Prepared %d training examples from %d samples",
            len(training_data), len(samples),
        )
        return training_data

    def train(self, training_data: list[dict[str, str]]) -> dict[str, Any]:
        """
        Run the fine-tuning process.

        Uses Hugging Face Transformers + PEFT (LoRA) for parameter-efficient
        fine-tuning. Falls back to a dry-run if dependencies are not available.

        Args:
            training_data: List of prompt-completion pairs.

        Returns:
            Dictionary with training results and model output path.
        """
        logger.info("=" * 60)
        logger.info("  Fine-Tuning Pipeline")
        logger.info("  Dataset: %s", self.config.dataset)
        logger.info("  Mode: %s", self.config.mode)
        logger.info("  Base Model: %s", self.config.base_model)
        logger.info("  Epochs: %d", self.config.epochs)
        logger.info("  Batch Size: %d", self.config.batch_size)
        logger.info("  Learning Rate: %s", self.config.learning_rate)
        logger.info("  LoRA Rank: %d", self.config.lora_rank)
        logger.info("  Training Examples: %d", len(training_data))
        logger.info("  Output: %s", self.output_dir)
        logger.info("=" * 60)

        try:
            return self._train_with_peft(training_data)
        except ImportError as exc:
            logger.warning(
                "PEFT/Transformers not available (%s). Running dry-run.",
                exc,
            )
            return self._dry_run(training_data)

    def _train_with_peft(self, training_data: list[dict[str, str]]) -> dict[str, Any]:
        """
        Fine-tune using Hugging Face Transformers + PEFT (LoRA).

        Args:
            training_data: Prepared training examples.

        Returns:
            Training results dictionary.
        """
        # Import required libraries
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
        )
        from peft import LoraConfig, get_peft_model, TaskType
        from datasets import Dataset

        logger.info("Loading tokenizer and model...")
        tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model,
            trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            trust_remote_code=True,
        )

        # Configure LoRA
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.config.lora_rank,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        )

        model = get_peft_model(model, lora_config)
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())
        logger.info(
            "Trainable parameters: %d / %d (%.2f%%)",
            trainable_params, total_params,
            100 * trainable_params / total_params,
        )

        # Prepare dataset
        def tokenize(example):
            full_text = example["prompt"] + example["completion"]
            return tokenizer(
                full_text,
                truncation=True,
                max_length=self.config.max_length,
                padding="max_length",
            )

        dataset = Dataset.from_list(training_data)
        tokenized = dataset.map(tokenize, remove_columns=dataset.column_names)

        # Split into train/eval
        split = tokenized.train_test_split(test_size=self.config.eval_split, seed=self.config.seed)

        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=self.config.epochs,
            per_device_train_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_steps=self.config.warmup_steps,
            logging_steps=self.config.log_steps,
            save_steps=self.config.save_steps,
            evaluation_strategy="steps",
            eval_steps=self.config.save_steps,
            fp16=self.config.fp16,
            seed=self.config.seed,
            report_to="none",
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=split["train"],
            eval_dataset=split["test"],
        )

        logger.info("Starting training...")
        train_result = trainer.train()

        # Save model
        model.save_pretrained(str(self.output_dir / "final_model"))
        tokenizer.save_pretrained(str(self.output_dir / "final_model"))

        results = {
            "status": "complete",
            "model_path": str(self.output_dir / "final_model"),
            "training_loss": train_result.training_loss,
            "epochs": self.config.epochs,
            "total_steps": train_result.global_step,
            "trainable_params": trainable_params,
        }

        logger.info("Training complete! Model saved to %s", results["model_path"])
        return results

    def _dry_run(self, training_data: list[dict[str, str]]) -> dict[str, Any]:
        """
        Perform a dry-run when PEFT/Transformers are not installed.

        Args:
            training_data: Training examples (not actually used for training).

        Returns:
            Dry-run results dictionary.
        """
        logger.info("DRY RUN — simulating training with %d examples", len(training_data))

        # Save training data to disk for inspection
        data_path = self.output_dir / "training_data.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(training_data[:10], f, indent=2)  # Save sample
        logger.info("Sample training data saved to %s", data_path)

        # Save config
        config_path = self.output_dir / "training_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({
                "dataset": self.config.dataset,
                "mode": self.config.mode,
                "base_model": self.config.base_model,
                "epochs": self.config.epochs,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "lora_rank": self.config.lora_rank,
                "total_examples": len(training_data),
            }, f, indent=2)

        results = {
            "status": "dry_run",
            "message": (
                "Dry run completed. Install transformers, peft, and datasets "
                "to perform actual fine-tuning."
            ),
            "training_data_path": str(data_path),
            "config_path": str(config_path),
            "total_examples": len(training_data),
        }

        logger.info("Dry run complete. Install dependencies for real training:")
        logger.info("  pip install transformers peft datasets torch")
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_dataset_loader(dataset_name: str, data_dir: str, mode: str) -> DatasetLoader:
    """
    Factory function to create the appropriate dataset loader.

    Args:
        dataset_name: Name of the dataset ('msrvtt' or 'activitynet').
        data_dir: Path to the dataset directory.
        mode: Training mode.

    Returns:
        DatasetLoader instance.
    """
    loaders = {
        "msrvtt": MSRVTTLoader,
        "activitynet": ActivityNetLoader,
    }

    loader_cls = loaders.get(dataset_name.lower())
    if loader_cls is None:
        raise ValueError(
            f"Unknown dataset '{dataset_name}'. Supported: {list(loaders.keys())}"
        )

    return loader_cls(data_dir, mode)


def main():
    """CLI entry point for the fine-tuning pipeline."""
    parser = argparse.ArgumentParser(
        description="CapturaAI Fine-Tuning Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backend.train_captioner --dataset msrvtt --data-dir ./data/msrvtt
  python -m backend.train_captioner --dataset activitynet --mode visual_only
  python -m backend.train_captioner --dataset msrvtt --epochs 5 --lr 1e-5
        """,
    )

    parser.add_argument(
        "--dataset", type=str, default="msrvtt",
        choices=["msrvtt", "activitynet"],
        help="Dataset to use for fine-tuning (default: msrvtt)",
    )
    parser.add_argument(
        "--data-dir", type=str, default="./data",
        help="Path to dataset directory (default: ./data)",
    )
    parser.add_argument(
        "--mode", type=str, default="audio_visual",
        choices=["audio_visual", "visual_only"],
        help="Training mode (default: audio_visual)",
    )
    parser.add_argument(
        "--output", type=str, default="./fine_tuned_models",
        help="Output directory for trained model (default: ./fine_tuned_models)",
    )
    parser.add_argument(
        "--epochs", type=int, default=3,
        help="Number of training epochs (default: 3)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Training batch size (default: 8)",
    )
    parser.add_argument(
        "--lr", type=float, default=2e-5,
        help="Learning rate (default: 2e-5)",
    )
    parser.add_argument(
        "--lora-rank", type=int, default=16,
        help="LoRA rank for parameter-efficient fine-tuning (default: 16)",
    )
    parser.add_argument(
        "--base-model", type=str,
        default="accounts/fireworks/models/llama-v3p1-8b-instruct",
        help="Base model identifier",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only prepare data, do not train",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Build config
    config = TrainingConfig(
        dataset=args.dataset,
        mode=args.mode,
        base_model=args.base_model,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        lora_rank=args.lora_rank,
        seed=args.seed,
    )

    # Load dataset
    logger.info("Loading dataset '%s' from %s...", args.dataset, args.data_dir)
    data_dir = Path(args.data_dir) / args.dataset
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created dataset directory: %s", data_dir)

    loader = get_dataset_loader(args.dataset, str(data_dir), args.mode)
    samples = loader.load()
    logger.info("Loaded %d samples", len(samples))

    if not samples:
        logger.error("No training samples found. Check your dataset directory.")
        sys.exit(1)

    # Prepare and train
    pipeline = TrainingPipeline(config)
    training_data = pipeline.prepare_dataset(samples)

    if args.dry_run:
        results = pipeline._dry_run(training_data)
    else:
        results = pipeline.train(training_data)

    # Print results
    logger.info("=" * 60)
    logger.info("  RESULTS")
    logger.info("=" * 60)
    for key, value in results.items():
        logger.info("  %s: %s", key, value)

    # Save results
    results_path = Path(args.output) / "results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Results saved to %s", results_path)


if __name__ == "__main__":
    main()
