"""Explicit primary-track commands; scoring never invokes a language model."""

import argparse
import asyncio
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def show_results(path):
    data = read(path)
    version = data["version"]
    count = data["case_count"]
    metric = data["ranking_metric"]
    if metric not in ("loss", "score"):
        raise ValueError("Unknown ranking metric")
    if not data["complete"] or any(r["scored"] != count for r in data["models"]):
        raise ValueError("A complete common-cohort result is required")
    print(f"{version} — lower {metric} is better")
    for title, rows in [
        ("Agents", sorted(data["models"], key=lambda r: r[metric])),
        ("Fixed policies", data["fixed_references"]),
    ]:
        print(f"\n{title}\n{'Model':26} {'Valid':>8} {'Loss':>10} {'Credits':>12}")
        for row in rows:
            print(
                f"{row['label']:26} {row['valid']:4}/{count} "
                f"{row['loss']:10.6f} {row['credits']:12,.1f}"
                + (f"  S={row['score']:.6f}" if metric == "score" else "")
            )


async def run_agent(args):
    from dotenv import load_dotenv

    from forecast_workflow.agents.runtime import code_hash, episode, exception_facts
    from forecast_workflow.core.io import write_json
    from forecast_workflow.core.schema import Task

    task = Task.model_validate(read(args.episode / "task.json"))
    args.output.mkdir(parents=True, exist_ok=False)
    trace, audit = [], []
    if args.provider == "local":
        from forecast_workflow.agents.local import LocalClient

        client = LocalClient(args.endpoint, args.seed, audit)
    else:
        from openai import AsyncOpenAI

        load_dotenv(Path.cwd() / ".env", override=False)
        client = AsyncOpenAI(max_retries=0)
    try:
        result = await episode(
            task,
            args.episode,
            client,
            args.model,
            args.effort if args.provider == "openai" else None,
            trace,
            budget_log=args.output / "ledger.json",
        )
    except Exception as exc:
        # Retain final text in the trace for deterministic offline normalization.
        result = {"status": "execution_error", "errors": exception_facts(exc)}
    finally:
        if args.provider == "openai":
            await client.close()
    result.update(
        task_id=task.task_id, model=args.model, provider=args.provider, code_sha256=code_hash()
    )
    write_json(args.output / "result.json", result)
    write_json(args.output / "trace.json", trace)
    if audit:
        write_json(args.output / "local_responses.json", audit)
    print(json.dumps({"task_id": task.task_id, "status": result["status"]}))


def main():
    parser = argparse.ArgumentParser(description="FWBench: forecast-driven decision evaluation")
    commands = parser.add_subparsers(dest="command", required=True)
    results = commands.add_parser("results", help="view saved aggregates; no API calls")
    results.add_argument("--input", type=Path, required=True)
    score = commands.add_parser("score", help="offline primary-contract scoring")
    score.add_argument("--contract", type=Path, required=True)
    score.add_argument(
        "--actual",
        type=Path,
        required=True,
        help="scorer-only JSON array of 24 values in the contract unit",
    )
    score.add_argument("--answer", type=Path, required=True, help="saved terminal answer text")
    score.add_argument("--output", type=Path, required=True)
    serve = commands.add_parser("serve", help="start primary MCP tools over visible episode inputs")
    serve.add_argument("--episode", type=Path, required=True)
    serve.add_argument("--as-of", required=True)
    run = commands.add_parser(
        "run", help="run one agent episode; OpenAI provider incurs API charges"
    )
    run.add_argument("--episode", type=Path, required=True)
    run.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new output directory; existing runs are not overwritten",
    )
    run.add_argument("--model", required=True)
    run.add_argument("--provider", choices=["local", "openai"], required=True)
    run.add_argument("--endpoint", default="http://127.0.0.1:8080")
    run.add_argument("--seed", type=int, default=1701)
    run.add_argument("--effort", default="high")
    args = parser.parse_args()
    if args.command == "results":
        show_results(args.input)
    elif args.command == "score":
        from forecast_workflow.core.io import write_json
        from forecast_workflow.evaluation.grading import grade
        from forecast_workflow.evaluation.normalization import normalize_terminal_answer

        normalized = normalize_terminal_answer(args.answer.read_text())
        result = grade(normalized.payload or {}, read(args.contract), read(args.actual))
        result["format_rejection"] = normalized.rejection
        write_json(args.output, result)
        print(json.dumps(result, indent=2))
    elif args.command == "serve":
        from forecast_workflow.tools.server import make_server

        make_server(args.episode, args.as_of).run()
    else:
        asyncio.run(run_agent(args))


if __name__ == "__main__":
    main()
