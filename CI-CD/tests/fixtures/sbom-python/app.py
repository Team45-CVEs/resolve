"""Test fixture: Python-only project. No CMake build, so no SBOM."""
import requests


def main():
    print(requests.__version__)


if __name__ == "__main__":
    main()
