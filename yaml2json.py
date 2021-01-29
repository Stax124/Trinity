import yaml
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("input", type=str)
parser.add_argument("output", type=str)
parser.add_argument("--reverse", action="store_true", default=False)
args = parser.parse_args()

if args.reverse:
    f_input = json.load(open(args.input, "r"))
    yaml.safe_dump(f_input, open(args.output, "w"))
    print("Done")
else:
    f_input = yaml.safe_load(open(args.input, "r"))
    json.dump(f_input, open(args.output, "w"))
    print("Done")


