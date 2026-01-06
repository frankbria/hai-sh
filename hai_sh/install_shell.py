"""
Shell integration installation helper for hai-sh.

This module provides a command-line utility to install shell integration
files (bash_integration.sh, zsh_integration.sh) to the user's ~/.hai/ directory.
"""

import shutil
import sys
from pathlib import Path
from typing import Optional

try:
    # Python 3.9+
    from importlib.resources import files
except ImportError:
    # Python 3.7-3.8 fallback
    from importlib.resources import path as resource_path


def get_package_integration_dir() -> Path:
    """
    Get the path to the integrations directory in the installed package.
    
    Returns:
        Path: Path to the integrations directory
    """
    try:
        # Modern approach (Python 3.9+)
        return files("hai_sh").joinpath("integrations")
    except (NameError, AttributeError):
        # Fallback for older Python versions
        import hai_sh.integrations
        return Path(hai_sh.integrations.__file__).parent


def get_hai_dir() -> Path:
    """Get the ~/.hai directory path."""
    return Path.home() / ".hai"


def copy_shell_integration_file(filename: str) -> tuple[bool, Optional[str]]:
    """
    Copy a shell integration file from package to ~/.hai/
    
    Args:
        filename: Name of the file to copy (e.g., "bash_integration.sh")
    
    Returns:
        tuple: (success: bool, error_message: Optional[str])
    """
    try:
        source_dir = get_package_integration_dir()
        dest_dir = get_hai_dir()
        
        # Ensure destination directory exists
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Get source and destination paths
        source_file = source_dir / filename
        dest_file = dest_dir / filename
        
        # For Python 3.9+ with Traversable objects
        if hasattr(source_file, 'read_text'):
            content = source_file.read_text()
            dest_file.write_text(content)
        else:
            # Fallback for regular Path objects
            if not source_file.exists():
                return False, f"Source file not found: {source_file}"
            shutil.copy2(source_file, dest_file)
        
        # Make shell scripts executable
        if filename.endswith('.sh'):
            dest_file.chmod(0o755)
        
        return True, None
        
    except Exception as e:
        return False, str(e)


def install_shell_integration(shell: Optional[str] = None) -> int:
    """
    Install shell integration files to ~/.hai/
    
    Args:
        shell: Specific shell to install ('bash' or 'zsh'), or None for both
    
    Returns:
        int: Exit code (0 = success, 1 = error)
    """
    hai_dir = get_hai_dir()
    
    print(f"Installing hai-sh shell integration to {hai_dir}/")
    print()
    
    # Determine which files to install
    files_to_install = []
    if shell is None or shell == 'bash':
        files_to_install.append('bash_integration.sh')
    if shell is None or shell == 'zsh':
        files_to_install.append('zsh_integration.sh')
    
    # Copy files
    errors = []
    installed = []
    
    for filename in files_to_install:
        success, error = copy_shell_integration_file(filename)
        if success:
            installed.append(filename)
            print(f"✓ Installed {filename}")
        else:
            errors.append(f"{filename}: {error}")
            print(f"✗ Failed to install {filename}: {error}")
    
    print()
    
    # Show errors if any
    if errors:
        print("Installation completed with errors.")
        return 1
    
    # Show success message and instructions
    print("✓ Shell integration installed successfully!")
    print()
    print("Next steps:")
    print()
    
    if 'bash_integration.sh' in installed:
        print("For Bash:")
        print(f"  Add this line to your ~/.bashrc:")
        print(f"  source {hai_dir}/bash_integration.sh")
        print()
    
    if 'zsh_integration.sh' in installed:
        print("For Zsh:")
        print(f"  Add this line to your ~/.zshrc:")
        print(f"  source {hai_dir}/zsh_integration.sh")
        print()
    
    print("Then reload your shell:")
    print("  source ~/.bashrc  # or source ~/.zshrc")
    print()
    print("Usage:")
    print("  Type a query, then press Ctrl+X Ctrl+H")
    print("  Or use the @hai prefix: @hai show me large files")
    print()
    
    return 0


def main():
    """Main entry point for hai-install-shell command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="hai-install-shell",
        description="Install hai-sh shell integration files",
        epilog="After installation, add the integration script to your shell's RC file."
    )
    parser.add_argument(
        '--shell',
        choices=['bash', 'zsh'],
        help="Install for specific shell only (default: both)"
    )
    parser.add_argument(
        '--version',
        action='version',
        version='hai-sh 0.1.2'
    )
    
    args = parser.parse_args()
    
    try:
        exit_code = install_shell_integration(args.shell)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
