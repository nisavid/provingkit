from pathlib import Path


def main():
    source = Path("data/source.csv")
    output = Path("output/report.csv")
    raise NotImplementedError(f"Generate {output} from {source}")


if __name__ == "__main__":
    main()
