"""The list of libraries each release carries (tools/make_sbom.py, run by .github/workflows/release.yml). It is built
from what `pip inspect` reports, so these hand it a made-up report: no pip, no network, nothing installed."""

from pathlib import Path

import pytest

from tools import make_sbom

ROOT = Path(__file__).resolve().parents[1]
MAC = {"python_version": "3.12", "sys_platform": "darwin", "implementation_name": "cpython", "os_name": "posix"}
WINDOWS = {**MAC, "sys_platform": "win32", "os_name": "nt"}
VERSIONS = {"python": "3.12.1", "qt": "6.12.0", "ffmpeg": "7.1", "timestamp": "2026-10-29T12:00:00Z"}


def package(name, version="1.0", requires=(), **metadata):
    return {"metadata": {"name": name, "version": version, "requires_dist": list(requires), **metadata}}


def sbom(installed, requirements="app\n", env=MAC):
    return make_sbom.build_sbom({"installed": installed, "environment": env}, requirements, "0.2.0", **VERSIONS)


def libraries(document):
    return {c["name"]: c for c in document["components"] if c["type"] == "library"}


# ------------------------------------------------------------------------------------ which packages are listed
def test_the_app_and_what_it_needs_are_listed_and_the_build_tools_are_not():
    document = sbom(
        [
            package("app", requires=["lib>=1"]),
            package("lib", requires=["deep"]),
            package("deep"),
            package("pyinstaller", requires=["deep"]),  # installed for the build, not needed by the app
            package("pytest"),
        ]
    )
    assert sorted(libraries(document)) == ["app", "deep", "lib"]


def test_a_package_two_others_need_is_listed_once():
    installed = [package("app", requires=["a", "b"]), package("a", requires=["c"]), package("b", requires=["c"])]
    assert sorted(libraries(sbom([*installed, package("c")]))) == ["a", "app", "b", "c"]


def test_requirements_txt_is_read_like_pip_reads_it():
    text = "# a comment\n-r other.txt\n\nPySide6==6.12.0  # pinned\nApp_One==1.0 \\\n    --hash=sha256:abc\n"
    assert make_sbom._requirement_names(text) == ["pyside6", "app-one"]


def test_a_package_that_is_named_but_not_installed_stops_the_script():
    with pytest.raises(ValueError, match="app.*isn't installed"):
        sbom([package("other")])


def test_a_needed_package_that_is_not_installed_stops_the_script():
    with pytest.raises(ValueError, match="app needs lib"):
        sbom([package("app", requires=["lib"])])


def test_extras_are_not_followed_and_never_ignored_quietly():
    assert sorted(libraries(sbom([package("app", requires=["extra-lib; extra == 'full'"]), package("extra-lib")]))) == [
        "app"
    ]
    with pytest.raises(ValueError, match="extras"):
        sbom([package("app", requires=["lib[socks]"]), package("lib")])
    with pytest.raises(ValueError, match="extras"):
        sbom([package("app")], "app[full]\n")


def test_a_package_only_some_machines_need_is_listed_where_it_applies():
    installed = [
        package("app", requires=['colorama; sys_platform == "win32"', 'tomli; python_version < "3.11"']),
        package("colorama"),
        package("tomli"),  # installed here for another reason, but this app doesn't need it on Python 3.12
    ]
    assert sorted(libraries(sbom(installed, env=MAC))) == ["app"]
    assert sorted(libraries(sbom(installed, env=WINDOWS))) == ["app", "colorama"]


def test_a_marker_it_cannot_read_counts_only_if_the_package_is_installed():
    requires = ["here; platform_hair == 'long'", "missing; platform_hair == 'long'"]
    assert sorted(libraries(sbom([package("app", requires=requires), package("here")]))) == ["app", "here"]


@pytest.mark.parametrize(
    ("marker", "holds"),
    [
        ('python_version < "3.11"', False),
        ('python_version >= "3.9"', True),
        ("python_version == '3.12'", True),
        ('python_version > "3.9" and sys_platform == "win32"', False),
        ('sys_platform == "win32" or sys_platform == "darwin"', True),
        ('implementation_name != "PyPy"', True),
        ('os_name not in "nt ce"', True),
        ('sys_platform in "win32 cygwin"', False),
        ('(python_version < "3.9" or sys_platform == "darwin") and implementation_name == "cpython"', True),
        ('sys_platform == "win32" and python_version < "3.9" or os_name == "posix"', True),  # `and` binds tighter
        ('"darwin" == sys_platform', True),
    ],
)
def test_environment_markers(marker, holds):
    assert make_sbom._marker_holds(marker, MAC) is holds


@pytest.mark.parametrize(
    "marker", ['python_version ~= "3.9"', "python_version <", 'sys_platform == "win32" and', "(os_name"]
)
def test_a_marker_it_cannot_read_is_an_error(marker):
    with pytest.raises(ValueError, match="Can't read"):
        make_sbom._marker_holds(marker, MAC)


# ------------------------------------------------------------------------------------ what each entry says
def test_a_library_has_a_name_a_version_and_a_package_url():
    found = libraries(sbom([package("PySide6_Essentials", "6.12.0")], "PySide6_Essentials\n"))["PySide6_Essentials"]
    assert found == {
        "type": "library",
        "name": "PySide6_Essentials",
        "version": "6.12.0",
        "purl": "pkg:pypi/pyside6-essentials@6.12.0",
    }


def test_a_version_with_a_plus_is_written_the_way_package_urls_want():
    assert libraries(sbom([package("app", "2.5.4+cpu")]))["app"]["purl"] == "pkg:pypi/app@2.5.4%2Bcpu"


def test_a_licence_is_listed_only_where_the_metadata_states_one():
    installed = [
        package("app", requires=["spdx", "named", "wordy", "silent"]),
        package("spdx", license_expression="Apache-2.0 OR BSD-2-Clause", license="ignored when there is an expression"),
        package("named", license="ISC"),
        package("wordy", license="Copyright (c) 2001\nPermission is hereby granted..."),
        package("silent"),
    ]
    found = libraries(sbom(installed))
    assert found["spdx"]["licenses"] == [{"expression": "Apache-2.0 OR BSD-2-Clause"}]
    assert found["named"]["licenses"] == [{"license": {"name": "ISC"}}]
    assert "licenses" not in found["wordy"]
    assert "licenses" not in found["silent"]


def test_the_app_python_qt_and_ffmpeg_are_listed_too():
    document = sbom([package("app")])
    assert document["metadata"]["component"] == {"type": "application", "name": "DJ Toolkit", "version": "0.2.0"}
    others = {c["name"]: c["version"] for c in document["components"] if c["type"] != "library"}
    assert others == {"Python": "3.12.1", "Qt": "6.12.0", "ffmpeg": "7.1"}


def test_the_document_has_the_fields_cyclonedx_1_5_asks_for_and_none_it_does_not_know():
    """Checked by hand against https://cyclonedx.org/schema/bom-1.5.schema.json: the document needs `bomFormat` and
    `specVersion`, a component needs `type` and `name`, and neither takes a field the schema doesn't list."""
    installed = [package("app", requires=["named"]), package("named", license="ISC")]
    document = sbom(installed)
    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"] == "1.5"
    assert set(document) <= {"$schema", "bomFormat", "specVersion", "version", "metadata", "components"}
    types = {"application", "framework", "library", "platform"}  # all in the schema's list for `type`
    for component in [document["metadata"]["component"], *document["components"]]:
        assert component["type"] in types
        assert component["name"]
        assert set(component) <= {"type", "name", "version", "purl", "description", "licenses"}
    assert make_sbom.SCHEMA.endswith("/bom-1.5.schema.json")


def test_the_same_report_gives_the_same_document():
    installed = [package("zed"), package("app", requires=["zed", "alpha"]), package("alpha")]
    assert sbom(installed) == sbom(list(reversed(installed)))
    assert [c["name"] for c in sbom(installed)["components"]][:3] == ["alpha", "app", "zed"]


def test_the_real_requirements_file_is_still_one_this_script_can_read():
    names = make_sbom._requirement_names((ROOT / "requirements.txt").read_text("utf8"))
    assert "pyside6" in names
    assert "imageio-ffmpeg" in names
