"""
Basic import tests for hai-sh package.

These tests verify that the package can be imported correctly
and has the expected structure and metadata.
"""

import pytest


@pytest.mark.unit
def test_import_hai_sh():
    """Test that the hai_sh package can be imported."""
    import hai_sh

    assert hai_sh is not None


@pytest.mark.unit
def test_version_exists():
    """Test that __version__ attribute exists and is a string."""
    import hai_sh

    assert hasattr(hai_sh, "__version__")
    assert isinstance(hai_sh.__version__, str)


@pytest.mark.unit
def test_version_format():
    """Test that version follows semantic versioning format."""
    import hai_sh

    version = hai_sh.__version__
    parts = version.split(".")

    # Should have at least major.minor.patch
    assert len(parts) >= 3, f"Version '{version}' should have at least 3 parts"

    # First three parts should be numeric
    for i, part in enumerate(parts[:3]):
        assert part.isdigit(), f"Version part {i} ('{part}') should be numeric"


@pytest.mark.unit
def test_version_matches_expected():
    """Test that version matches expected value from pyproject.toml."""
    import hai_sh

    # v0.1 should have version 0.0.1
    assert hai_sh.__version__ == "0.0.1"


@pytest.mark.unit
def test_package_has_main():
    """Test that __main__ module exists for CLI entry point."""
    import hai_sh.__main__

    assert hai_sh.__main__ is not None
    assert hasattr(hai_sh.__main__, "main")
    assert callable(hai_sh.__main__.main)


@pytest.mark.unit
def test_main_function_signature():
    """Test that main() function has correct signature."""
    import inspect
    import hai_sh.__main__

    main_func = hai_sh.__main__.main
    sig = inspect.signature(main_func)

    # main() should take no required arguments
    params = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty]
    assert len(params) == 0, "main() should not have required parameters"
