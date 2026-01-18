"""
Evaluate filter precision/recall against labeled data.

Usage:
    python evaluate.py                    # Evaluate against all files in data/labeled/
    python evaluate.py --golden           # Evaluate against data/golden/golden-test-set.json only
    python evaluate.py --file PATH        # Evaluate against specific file
    python evaluate.py --verbose          # Show per-item results
"""

import argparse
import json
import sys
from pathlib import Path

from sklearn.metrics import precision_score, recall_score, f1_score

from scraper import description_matches


def load_labeled_data(filepath: Path) -> list[dict]:
    """
    Load labeled items from JSON file.

    Supports two formats:
    1. Wrapped format: {"metadata": {...}, "items": [...]}
    2. Raw array format: [...]

    Required fields per item: description, label (boolean)

    Args:
        filepath: Path to JSON file

    Returns:
        List of labeled items

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
        ValueError: If required fields are missing or invalid
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {filepath}: {e.msg}",
                e.doc,
                e.pos
            )

    # Handle both wrapped (with metadata) and raw array formats
    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(f"Expected dict or list at root of {filepath}, got {type(data).__name__}")

    if not items:
        return []

    # Validate required fields
    for i, item in enumerate(items):
        if "description" not in item:
            raise ValueError(f"Item {i} in {filepath} missing required 'description' field")
        if "label" not in item:
            raise ValueError(f"Item {i} in {filepath} missing required 'label' field")
        if not isinstance(item["label"], bool):
            raise ValueError(
                f"Item {i} in {filepath} 'label' must be boolean, got {type(item['label']).__name__}"
            )

    return items


def evaluate(items: list[dict], verbose: bool = False) -> dict:
    """
    Run filter against labeled items and compute metrics.

    Args:
        items: List of labeled items with 'description' and 'label' fields
        verbose: If True, print per-item results

    Returns:
        Dictionary with metrics:
        - precision, recall, f1 (0-1 floats)
        - total, positives, negatives (counts)
        - true_positives, false_positives, false_negatives, true_negatives (counts)
    """
    if not items:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "total": 0,
            "positives": 0,
            "negatives": 0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_negatives": 0,
        }

    y_true = []
    y_pred = []

    for item in items:
        expected = item["label"]
        predicted = description_matches(item["description"])

        y_true.append(expected)
        y_pred.append(predicted)

        if verbose:
            item_id = item.get("id", item.get("company", f"item_{len(y_true)}"))
            match_status = "MATCH" if expected == predicted else "MISMATCH"
            print(f"  [{match_status}] {item_id}: expected={expected}, predicted={predicted}")

    # Compute confusion matrix components
    true_positives = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    false_positives = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    false_negatives = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    true_negatives = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)

    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "total": len(items),
        "positives": sum(y_true),
        "negatives": len(y_true) - sum(y_true),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
    }


def print_report(metrics: dict, source: str) -> None:
    """
    Pretty-print evaluation metrics.

    Args:
        metrics: Dictionary from evaluate()
        source: Description of data source (file path or directory)
    """
    print()
    print("=" * 60)
    print(f"EVALUATION REPORT: {source}")
    print("=" * 60)
    print()

    # Summary metrics
    print("METRICS")
    print("-" * 40)
    print(f"  Precision: {metrics['precision']:.2%}")
    print(f"  Recall:    {metrics['recall']:.2%}")
    print(f"  F1 Score:  {metrics['f1']:.2%}")
    print()

    # Dataset breakdown
    print("DATASET")
    print("-" * 40)
    print(f"  Total items:  {metrics['total']}")
    print(f"  Positives:    {metrics['positives']} (labeled as qualified)")
    print(f"  Negatives:    {metrics['negatives']} (labeled as rejected)")
    print()

    # Confusion matrix
    print("CONFUSION MATRIX")
    print("-" * 40)
    print()
    print("                      Predicted")
    print("                  Reject    Qualify")
    print(f"  Actual Reject   {metrics['true_negatives']:>6}    {metrics['false_positives']:>6}  (TN, FP)")
    print(f"  Actual Qualify  {metrics['false_negatives']:>6}    {metrics['true_positives']:>6}  (FN, TP)")
    print()

    # Interpretation
    print("INTERPRETATION")
    print("-" * 40)
    print(f"  True Positives:  {metrics['true_positives']:>4} (correctly identified as qualified)")
    print(f"  False Positives: {metrics['false_positives']:>4} (incorrectly identified as qualified)")
    print(f"  False Negatives: {metrics['false_negatives']:>4} (missed qualified leads)")
    print(f"  True Negatives:  {metrics['true_negatives']:>4} (correctly rejected)")
    print()
    print("=" * 60)


def main() -> int:
    """
    Main entry point for CLI.

    Returns:
        Exit code: 0 on success, 1 on error
    """
    parser = argparse.ArgumentParser(
        description="Evaluate filter precision/recall against labeled data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evaluate.py                    # Evaluate all files in data/labeled/
  python evaluate.py --golden           # Evaluate golden test set only
  python evaluate.py --file data.json   # Evaluate specific file
  python evaluate.py --verbose          # Show per-item results
        """
    )
    parser.add_argument(
        "--golden",
        action="store_true",
        help="Evaluate against data/golden/golden-test-set.json only"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Evaluate against specific file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-item results (expected vs predicted)"
    )

    args = parser.parse_args()

    # Determine which files to evaluate
    base_dir = Path(__file__).parent

    try:
        if args.file:
            # Specific file
            files = [args.file]
            source = str(args.file)
        elif args.golden:
            # Golden test set
            golden_file = base_dir / "data" / "golden" / "golden-test-set.json"
            files = [golden_file]
            source = str(golden_file)
        else:
            # All files in data/labeled/
            labeled_dir = base_dir / "data" / "labeled"
            if not labeled_dir.exists():
                print(f"Error: Labeled data directory not found: {labeled_dir}")
                return 1
            files = list(labeled_dir.glob("*.json"))
            if not files:
                print(f"Warning: No JSON files found in {labeled_dir}")
                print("Add labeled data files to evaluate.")
                return 0
            source = f"{len(files)} file(s) in {labeled_dir}"

        # Load and combine all items
        all_items = []
        for filepath in files:
            try:
                items = load_labeled_data(filepath)
                if args.verbose:
                    print(f"\nLoaded {len(items)} items from {filepath}")
                all_items.extend(items)
            except FileNotFoundError as e:
                print(f"Error: {e}")
                return 1
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON - {e}")
                return 1
            except ValueError as e:
                print(f"Error: {e}")
                return 1

        if not all_items:
            print("Warning: No labeled items found to evaluate.")
            return 0

        # Run evaluation
        if args.verbose:
            print("\nEvaluating items:")

        metrics = evaluate(all_items, verbose=args.verbose)

        # Print report
        print_report(metrics, source)

        return 0

    except Exception as e:
        print(f"Error: Unexpected error - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
