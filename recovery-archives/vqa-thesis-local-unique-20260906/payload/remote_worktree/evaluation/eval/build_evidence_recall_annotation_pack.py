#!/usr/bin/env python3
"""Build timestamped contact sheets and score human evidence annotations."""

import argparse
import json
import math
from pathlib import Path

OBSERVABLE = {"visual", "audio", "visual_audio", "partial"}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    Path(path).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def parse_method(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("method must be NAME=RESULT_DIR")
    name, root = value.split("=", 1)
    return name, Path(root)


def index_evidence(root):
    indexed = {}
    for path in root.glob("**/evidence.json"):
        data = load_json(path)
        qid = str(data.get("question_id", path.parent.name))
        if qid in indexed:
            raise RuntimeError(f"duplicate evidence for {qid} under {root}")
        indexed[qid] = data
    return indexed


def video_metadata(video_path):
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 1.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return {
        "frame_count": frame_count,
        "fps": fps,
        "duration_sec": max(0.0, (frame_count - 1) / fps),
        "width": width,
        "height": height,
    }


def uniform_indices(frame_count, count):
    if count <= 1:
        return [0]
    return [round(i * max(0, frame_count - 1) / (count - 1)) for i in range(count)]


def read_frame(cap, frame_index):
    import cv2
    from PIL import Image

    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"failed to decode frame {frame_index}")
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def sample_ranks(evidence):
    ranks = set()
    for item in evidence.get("selected_frames", []):
        if item.get("sample_rank") is not None:
            ranks.add(int(item["sample_rank"]))
    return ranks


def render_contact_sheet(video_path, metadata, method_evidence, output_path, count, thumb_width):
    import cv2
    from PIL import Image, ImageDraw, ImageFont

    indices = uniform_indices(metadata["frame_count"], count)
    ratio = metadata["height"] / max(1, metadata["width"])
    thumb_height = max(90, round(thumb_width * ratio))
    cols = 4
    rows = math.ceil(count / cols)
    label_height = 34
    sheet = Image.new("RGB", (cols * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    rank_sets = {name: sample_ranks(evidence) for name, evidence in method_evidence.items()}
    cap = cv2.VideoCapture(str(video_path))
    for rank, frame_index in enumerate(indices):
        image = read_frame(cap, frame_index)
        image.thumbnail((thumb_width, thumb_height))
        x = (rank % cols) * thumb_width
        y = (rank // cols) * (thumb_height + label_height)
        tile = Image.new("RGB", (thumb_width, thumb_height), "black")
        tile.paste(image, ((thumb_width - image.width) // 2, (thumb_height - image.height) // 2))
        sheet.paste(tile, (x, y))
        timestamp = frame_index / metadata["fps"]
        tags = [name for name, ranks in rank_sets.items() if rank in ranks]
        draw.rectangle((x, y + thumb_height, x + thumb_width, y + thumb_height + label_height), fill="white")
        draw.text((x + 4, y + thumb_height + 2), f"r{rank:02d}  {timestamp:6.2f}s  f{frame_index}", fill="black", font=font)
        draw.text((x + 4, y + thumb_height + 17), " ".join(tags) or "-", fill=(0, 75, 160), font=font)
    cap.release()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=90)


def selected_timestamps(evidence, metadata):
    timestamps = []
    for item in evidence.get("selected_frames", []):
        if item.get("timestamp_sec") is not None:
            timestamps.append(float(item["timestamp_sec"]))
        elif item.get("frame_index") is not None:
            timestamps.append(float(item["frame_index"]) / metadata["fps"])
    return timestamps


def item_timestamp(item, metadata):
    if item.get("timestamp_sec") is not None:
        return float(item["timestamp_sec"])
    if item.get("frame_index") is not None:
        return float(item["frame_index"]) / metadata["fps"]
    return None


def submitted_local_items(evidence):
    selected = evidence.get("selected_local_views")
    if isinstance(selected, list):
        return selected
    visual_plan = evidence.get("visual_plan")
    if isinstance(visual_plan, list):
        return [item for item in visual_plan if item.get("view_type") == "local"]
    return evidence.get("crop_metas") or []


def local_timestamps(evidence, metadata):
    return [timestamp for item in submitted_local_items(evidence)
            if (timestamp := item_timestamp(item, metadata)) is not None]


def separate_local_timestamps(evidence, metadata):
    return [timestamp for item in submitted_local_items(evidence)
            if item.get("submission_mode") != "embedded_focus_context"
            if (timestamp := item_timestamp(item, metadata)) is not None]


def local_views(evidence, metadata):
    normalized = []
    for item in submitted_local_items(evidence):
        timestamp = item_timestamp(item, metadata)
        bbox = item.get("bbox_norm")
        if bbox is None and item.get("bbox") and metadata.get("width") and metadata.get("height"):
            x1, y1, x2, y2 = item["bbox"]
            bbox = [x1 / metadata["width"], y1 / metadata["height"],
                    x2 / metadata["width"], y2 / metadata["height"]]
        if timestamp is not None and bbox and len(bbox) == 4:
            normalized.append((float(timestamp), [float(v) for v in bbox]))
    return normalized


def in_intervals(timestamp, intervals, tolerance):
    return any(float(start) - tolerance <= timestamp <= float(end) + tolerance for start, end in intervals)


def contains_center(container, target):
    cx = (target[0] + target[2]) / 2
    cy = (target[1] + target[3]) / 2
    return container[0] <= cx <= container[2] and container[1] <= cy <= container[3]


def score_annotations(rows, evidence_by_method, metadata_by_qid, tolerance):
    summary = {name: {"eligible": 0, "any_hit": 0, "units": 0, "unit_hits": 0,
                      "visual_units": 0, "visual_hits": 0, "region_units": 0, "region_hits": 0,
                      "global_frames": 0, "global_frame_hits": 0,
                      "input_views": 0, "input_view_hits": 0}
               for name in evidence_by_method}
    details = []
    for row in rows:
        if row.get("annotation_status") != "complete" or row.get("evidence_observability") not in OBSERVABLE:
            continue
        qid = str(row["question_id"])
        units = [unit for unit in row.get("evidence_units", []) if unit.get("required", True)]
        if not units:
            continue
        detail = {"question_id": qid, "methods": {}}
        for name, indexed in evidence_by_method.items():
            evidence = indexed.get(qid, {})
            metadata = metadata_by_qid[qid]
            timestamps = selected_timestamps(evidence, metadata)
            local_ts = local_timestamps(evidence, metadata)
            separate_local_ts = separate_local_timestamps(evidence, metadata)
            crops = local_views(evidence, metadata)
            visual_intervals = [
                interval
                for unit in units
                if "visual" in set(unit.get("modalities", []))
                for interval in unit.get("intervals_sec", [])
            ]
            global_frame_hits = sum(in_intervals(ts, visual_intervals, tolerance) for ts in timestamps)
            local_view_hits = sum(in_intervals(ts, visual_intervals, tolerance) for ts in separate_local_ts)
            unit_hits = []
            visual_hits = []
            region_hits = []
            for unit in units:
                intervals = unit.get("intervals_sec", [])
                modalities = set(unit.get("modalities", []))
                visual_hit = any(in_intervals(ts, intervals, tolerance) for ts in timestamps) if "visual" in modalities else None
                audio_hit = "audio" in modalities
                temporal_hit = audio_hit or bool(visual_hit)
                bbox = unit.get("bbox_norm")
                region_hit = None
                if bbox:
                    region_hit = any(in_intervals(ts, intervals, tolerance) and contains_center(crop, bbox)
                                     for ts, crop in crops)
                    temporal_hit = temporal_hit and region_hit
                unit_hits.append(bool(temporal_hit))
                if visual_hit is not None:
                    visual_hits.append(bool(visual_hit))
                if region_hit is not None:
                    region_hits.append(bool(region_hit))
            stats = summary[name]
            stats["eligible"] += 1
            stats["any_hit"] += int(any(unit_hits))
            stats["units"] += len(unit_hits)
            stats["unit_hits"] += sum(unit_hits)
            stats["visual_units"] += len(visual_hits)
            stats["visual_hits"] += sum(visual_hits)
            stats["region_units"] += len(region_hits)
            stats["region_hits"] += sum(region_hits)
            stats["global_frames"] += len(timestamps)
            stats["global_frame_hits"] += global_frame_hits
            stats["input_views"] += len(timestamps) + len(separate_local_ts)
            stats["input_view_hits"] += global_frame_hits + local_view_hits
            detail["methods"][name] = {
                "unit_hits": unit_hits,
                "visual_hits": visual_hits,
                "any_hit": any(unit_hits),
                "region_hits": region_hits,
                "global_frame_hits": global_frame_hits,
                "global_frame_count": len(timestamps),
                "input_view_hits": global_frame_hits + local_view_hits,
                "input_view_count": len(timestamps) + len(separate_local_ts),
            }
        details.append(detail)
    for stats in summary.values():
        stats["evidence_recall_any"] = stats["any_hit"] / stats["eligible"] if stats["eligible"] else None
        stats["evidence_unit_recall"] = stats["unit_hits"] / stats["units"] if stats["units"] else None
        stats["visual_evidence_recall"] = stats["visual_hits"] / stats["visual_units"] if stats["visual_units"] else None
        stats["region_recall"] = stats["region_hits"] / stats["region_units"] if stats["region_units"] else None
        stats["global_evidence_precision"] = (
            stats["global_frame_hits"] / stats["global_frames"] if stats["global_frames"] else None
        )
        stats["input_view_evidence_precision"] = (
            stats["input_view_hits"] / stats["input_views"] if stats["input_views"] else None
        )
    return summary, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--groundtruth-file", required=True)
    parser.add_argument("--asr-file", required=True)
    parser.add_argument("--video-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--method", action="append", type=parse_method, default=[])
    parser.add_argument("--sample-count", type=int, default=32)
    parser.add_argument("--thumbnail-width", type=int, default=240)
    parser.add_argument("--tolerance-sec", type=float, default=0.5)
    parser.add_argument("--annotation-overlay", default="")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    questions = {str(row["question_id"]): row for row in load_json(args.question_file)}
    groundtruth = {str(row["question_id"]): row for row in load_json(args.groundtruth_file)}
    asr_data = load_json(args.asr_file)
    evidence_by_method = {name: index_evidence(root) for name, root in args.method}
    previous = {str(row["question_id"]): row for row in load_jsonl(output_dir / "annotations.jsonl")}
    overlay = {}
    if args.annotation_overlay:
        overlay_path = Path(args.annotation_overlay)
        overlay_rows = load_json(overlay_path) if overlay_path.suffix == ".json" else load_jsonl(overlay_path)
        overlay = {str(row["question_id"]): row for row in overlay_rows}
    metadata_by_qid = {}
    rows = []

    for qid, question in questions.items():
        gt = groundtruth[qid]
        video_id = str(question["video"])
        video_path = Path(args.video_dir) / f"{video_id}.mp4"
        metadata = video_metadata(video_path)
        metadata_by_qid[qid] = metadata
        method_evidence = {name: indexed.get(qid, {}) for name, indexed in evidence_by_method.items()}
        old = {**previous.get(qid, {}), **overlay.get(qid, {})}
        row = {
            "question_id": qid,
            "video_id": video_id,
            "primary_type": question.get("question_type", [None])[0],
            "question": question.get("question", ""),
            "answer": gt.get("answer", ""),
            "meta_info": gt.get("meta_info", ""),
            "asr": (asr_data.get(video_id) or asr_data.get(f"{video_id}.mp4") or "")
            if isinstance(asr_data, dict) else "",
            "video": metadata,
            "contact_sheet": f"contact_sheets/{qid}.jpg",
            "annotation_status": old.get("annotation_status", "pending"),
            "evidence_observability": old.get("evidence_observability", "unknown"),
            "decisive_fact": old.get("decisive_fact", gt.get("answer", "")),
            "evidence_units": old.get("evidence_units", []),
            "notes": old.get("notes", ""),
        }
        rows.append(row)
        if not args.skip_render:
            render_contact_sheet(
                video_path,
                metadata,
                method_evidence,
                output_dir / row["contact_sheet"],
                args.sample_count,
                args.thumbnail_width,
            )

    write_jsonl(output_dir / "annotations.jsonl", rows)
    summary, details = score_annotations(rows, evidence_by_method, metadata_by_qid, args.tolerance_sec)
    (output_dir / "evidence_recall_summary.json").write_text(
        json.dumps({"methods": summary, "tolerance_sec": args.tolerance_sec}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "evidence_recall_details.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(rows), "completed": sum(r["annotation_status"] == "complete" for r in rows),
                      "methods": list(evidence_by_method), "output_dir": str(output_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
