"""Build TfL hourly cases from checksum-verified official trip archives."""

import argparse

from forecast_workflow.datasets.transport import build

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="configs/transport-construction.json")
    parser.add_argument("--profile", default="configs/transport-tariff.json")
    args = parser.parse_args()
    build(args.source, args.output, args.config, args.profile)
