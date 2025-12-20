"""
CLI entry point for hai-sh.
"""

import argparse
import sys
from hai_sh import __version__


def main():
    """Main entry point for the hai-sh CLI."""
    parser = argparse.ArgumentParser(
        prog="hai-sh",
        description="AI-powered terminal assistant for natural language command generation",
        epilog="For more information, visit: https://github.com/frankbria/hai-sh"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"hai-sh version {__version__}"
    )

    # For v0.1, just handle version display
    # Future versions will add more commands and functionality
    parser.add_argument(
        "query",
        nargs="*",
        help="Natural language query (coming in v0.1)"
    )

    args = parser.parse_args()

    # Placeholder for future functionality
    if args.query:
        print("hai-sh v0.1 is under development.")
        print("Command execution will be available soon!")
        print(f"\nYou asked: {' '.join(args.query)}")
        return 0

    # If no arguments, show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
