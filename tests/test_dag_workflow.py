#!/usr/bin/env python3
"""
Unit tests for the workflow-aware DAG generation.

These tests exercise:
  - WorkflowSet parsing from config data
  - AlignmentConfig.workflow_sets / iters / iter_info
  - Single reco submit file per iteration (queue-from-list)
  - Per-step millepede submit files
  - Correct DAG dependency structure
"""

import json
import sys
import os
import pytest
from pathlib import Path

# Allow importing from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AlignmentConfig import AlignmentConfig, WorkflowSet
from dag_manager import DAGManager


# ---------------------------------------------------------------------------
# Minimal template content for the tests
# ---------------------------------------------------------------------------

RECO_TPL = (
    "# reco iter {iter}\n"
    "executable = {exe_path}\n"
    "output = {logs_dir}/reco_iter{iter}_$(file_str).out\n"
    "error  = {logs_dir}/reco_iter{iter}_$(file_str).err\n"
    "log    = {log_path}\n"
    "arguments = {year} {run} {stations} $(file_str)"
    " {reco_dir} {kfalign_dir} {src_dir} {calypso_asetup} {calypso_setup}\n"
    "queue file_str from (\n"
    "{file_list})\n"
)

MILLE_TPL = (
    "# mille iter {iter} step {step}\n"
    "executable = {exe_path}\n"
    "output = {out_path}\n"
    "error  = {err_path}\n"
    "log    = {log_path}\n"
    "arguments = {to_next_iter} {src_dir} {kfalign_dir}"
    " {next_reco_dir} {env_pede} {env_root} {fix_rules}\n"
    "queue\n"
)

INPUT_ALIGN_TXT = "# dummy inputforalign\n"


# ---------------------------------------------------------------------------
# Pytest fixture: create a complete mock environment in a temp directory
# ---------------------------------------------------------------------------

@pytest.fixture
def env(tmp_path):
    """Set up mock directories, scripts, and templates for testing."""
    src_dir   = tmp_path / "src";   src_dir.mkdir()
    tpl_dir   = tmp_path / "tpl";   tpl_dir.mkdir()
    dag_base  = tmp_path / "dag";   dag_base.mkdir()
    data_base = tmp_path / "data";  data_base.mkdir()
    env_dir   = tmp_path / "env";   env_dir.mkdir()

    # Template files
    (tpl_dir / "reco.sub.tpl").write_text(RECO_TPL)
    (tpl_dir / "mille.sub.tpl").write_text(MILLE_TPL)
    (tpl_dir / "runAlignment.sh").write_text("#!/bin/bash\n")
    (tpl_dir / "runMillepede.sh").write_text("#!/bin/bash\n")
    (tpl_dir / "align_test.txt").write_text(INPUT_ALIGN_TXT)

    # Mock environment files
    (env_dir / "asetup.faser").write_text("# asetup\n")
    (env_dir / "setup.sh").write_text("#!/bin/bash\n")
    pede_dir = env_dir / "pede"; pede_dir.mkdir()
    (env_dir / "thisroot.sh").write_text("#!/bin/bash\n")

    return {
        "src_dir":   src_dir,
        "tpl_dir":   tpl_dir,
        "dag_base":  dag_base,
        "data_base": data_base,
        "env_dir":   env_dir,
    }


def _make_config(tmp_path, env, workflow: dict, raw_iters: int = 5,
                 files: str = "100-103") -> Path:
    """Write a minimal config.json and return its path."""
    cfg = {
        "raw": {
            "year": 2022,
            "run":  8294,
            "files": files,
            "iters": raw_iters,
            "stations": 4,
            "format": "Y{year}_R{run}_F{files}_ST{stations}",
        },
        "workflow": workflow,
        "dag": {
            "dir": str(env["dag_base"] / "{format}"),
            "file": "alignment.dag",
            "recoexe": "runAlignment.sh",
            "milleexe": "runMillepede.sh",
            "iter": {
                "dir": "iter{iter}",
                "recojob": "reco_iter{iter}",
                "recosub": "reco_iter{iter}.sub",
                "millejob": "millepede_iter{iter}_{step}",
                "millesub": "millepede_iter{iter}_{step}.sub",
                "logs": {
                    "dir": "logs_iter{iter}",
                    "recolog": "reco_iter{iter}.log",
                    "milleerr": "millepede_iter{iter}_{step}.err",
                    "millelog": "millepede_iter{iter}_{step}.log",
                    "milleout": "millepede_iter{iter}_{step}.out",
                },
            },
        },
        "data": {
            "dir": str(env["data_base"] / "{format}"),
            "config": "config.json",
            "initial": "inputforalign.txt",
            "iter": {
                "dir": "iter{iter}",
                "reco": "1reco",
                "kfalign": "2kfalignment",
                "millepede": "3millepede",
            },
        },
        "tpl": {
            "dir": str(env["tpl_dir"]),
            "recosub": "reco.sub.tpl",
            "recoexe": "runAlignment.sh",
            "millesub": "mille.sub.tpl",
            "milleexe": "runMillepede.sh",
            "inputforalign": "align_test.txt",
        },
        "src": {
            "dir": str(env["src_dir"]),
        },
        "env": {
            "calypso": {
                "asetup": str(env["env_dir"] / "asetup.faser"),
                "setup":  str(env["env_dir"] / "setup.sh"),
            },
            "pede": str(env["env_dir"] / "pede"),
            "root": str(env["env_dir"] / "thisroot.sh"),
        },
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2))
    return cfg_path


# ===========================================================================
# 1. WorkflowSet unit tests
# ===========================================================================

class TestWorkflowSet:
    def test_basic_parsing(self):
        data = {
            "iters": 10,
            "comment": "3ST Alignment",
            "pede": {
                "step0": ["IFT", 21, 41],
                "step1": ["IFT", 20, 22],
            },
        }
        ws = WorkflowSet("set0", data)
        assert ws.name == "set0"
        assert ws.iters == 10
        assert ws.comment == "3ST Alignment"
        assert list(ws.pede_steps.keys()) == ["step0", "step1"]
        assert ws.pede_steps["step0"] == ["IFT", 21, 41]
        assert ws.pede_steps["step1"] == ["IFT", 20, 22]

    def test_missing_pede_defaults_to_single_step(self):
        ws = WorkflowSet("set0", {"iters": 5})
        assert "step0" in ws.pede_steps
        assert ws.pede_steps["step0"] == []

    def test_empty_pede_defaults_to_single_step(self):
        ws = WorkflowSet("set0", {"iters": 3, "pede": {}})
        assert "step0" in ws.pede_steps

    def test_steps_are_sorted(self):
        data = {
            "iters": 2,
            "pede": {"step1": [1], "step0": [0]},
        }
        ws = WorkflowSet("set0", data)
        assert list(ws.pede_steps.keys()) == ["step0", "step1"]

    def test_repr(self):
        ws = WorkflowSet("set0", {"iters": 3})
        assert "set0" in repr(ws)


# ===========================================================================
# 2. AlignmentConfig.workflow_sets / iters / iter_info
# ===========================================================================

class TestAlignmentConfigWorkflow:
    WORKFLOW = {
        "set0": {"iters": 10, "pede": {"step0": ["IFT", 21, 41],
                                        "step1": ["IFT", 20, 22]}},
        "set1": {"iters": 10, "pede": {"step0": ["side", "3ST"]}},
        "set2": {"iters": 10, "pede": {"step0": ["layer", "3ST"]}},
    }

    def test_workflow_sets_count(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW)
        config = AlignmentConfig(cfg_path)
        assert len(config.workflow_sets) == 3

    def test_workflow_sets_order(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW)
        config = AlignmentConfig(cfg_path)
        names = [ws.name for ws in config.workflow_sets]
        assert names == ["set0", "set1", "set2"]

    def test_iters_total_from_workflow(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW, raw_iters=999)
        config = AlignmentConfig(cfg_path)
        # workflow total = 10 + 10 + 10 = 30, raw.iters (999) is ignored
        assert config.iters == 30

    def test_iters_fallback_to_raw(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, workflow={}, raw_iters=7)
        config = AlignmentConfig(cfg_path)
        # empty workflow → fallback to raw.iters
        assert config.iters == 7

    def test_iter_info_first_set(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW)
        config = AlignmentConfig(cfg_path)
        ws, local = config.iter_info(0)
        assert ws.name == "set0"
        assert local == 0

    def test_iter_info_last_in_first_set(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW)
        config = AlignmentConfig(cfg_path)
        ws, local = config.iter_info(9)
        assert ws.name == "set0"
        assert local == 9

    def test_iter_info_second_set(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW)
        config = AlignmentConfig(cfg_path)
        ws, local = config.iter_info(10)
        assert ws.name == "set1"
        assert local == 0

    def test_iter_info_third_set(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW)
        config = AlignmentConfig(cfg_path)
        ws, local = config.iter_info(20)
        assert ws.name == "set2"
        assert local == 0

    def test_iter_info_out_of_range(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW)
        config = AlignmentConfig(cfg_path)
        with pytest.raises(ValueError):
            config.iter_info(30)


# ===========================================================================
# 3. DAGManager — reco submit files (one per iteration)
# ===========================================================================

class TestRecoSubmitFiles:
    WORKFLOW_2ITER = {
        "set0": {"iters": 2, "pede": {"step0": ["IFT"]}},
    }

    def test_one_reco_sub_per_iteration(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW_2ITER,
                                files="100-103")
        config  = AlignmentConfig(cfg_path)
        manager = DAGManager(config)
        manager.create_data_dirs()
        manager.create_dag_dirs()
        import shutil as _shutil
        _shutil.copy(config.tpl_recoexe, config.dag_recoexe)

        manager.create_reco_submit_files()

        # Exactly 2 submit files (one per iteration, NOT one per file)
        sub_files = list(config.dag_dir.rglob("reco_iter*.sub"))
        assert len(sub_files) == 2, f"Expected 2 reco sub files, got {len(sub_files)}"

    def test_reco_sub_contains_all_files(self, tmp_path, env):
        """The single reco submit file must list all file numbers.

        RawList('100-103') is exclusive-end: files 100, 101, 102 only.
        """
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW_2ITER,
                                files="100-103")
        config  = AlignmentConfig(cfg_path)
        manager = DAGManager(config)
        manager.create_data_dirs()
        manager.create_dag_dirs()
        import shutil as _shutil
        _shutil.copy(config.tpl_recoexe, config.dag_recoexe)

        manager.create_reco_submit_files()

        sub_path = config.dag_recosub(0)
        content  = sub_path.read_text()
        # files 100-103 (exclusive end) → 00100, 00101, 00102; NOT 00103
        assert "00100" in content
        assert "00101" in content
        assert "00102" in content
        assert "00103" not in content

    def test_reco_sub_uses_queue_from_syntax(self, tmp_path, env):
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW_2ITER,
                                files="100-102")
        config  = AlignmentConfig(cfg_path)
        manager = DAGManager(config)
        manager.create_data_dirs()
        manager.create_dag_dirs()
        import shutil as _shutil
        _shutil.copy(config.tpl_recoexe, config.dag_recoexe)

        manager.create_reco_submit_files()

        content = config.dag_recosub(0).read_text()
        assert "queue file_str from" in content

    def test_reco_sub_uses_htcondor_variable(self, tmp_path, env):
        """output/error lines must use the HTCondor $(file_str) variable."""
        cfg_path = _make_config(tmp_path, env, self.WORKFLOW_2ITER,
                                files="100-101")
        config  = AlignmentConfig(cfg_path)
        manager = DAGManager(config)
        manager.create_data_dirs()
        manager.create_dag_dirs()
        import shutil as _shutil
        _shutil.copy(config.tpl_recoexe, config.dag_recoexe)

        manager.create_reco_submit_files()

        content = config.dag_recosub(0).read_text()
        assert "$(file_str)" in content


# ===========================================================================
# 4. DAGManager — millepede submit files (one per step per iteration)
# ===========================================================================

class TestMilleSubmitFiles:
    WORKFLOW_2STEPS = {
        "set0": {
            "iters": 2,
            "pede": {
                "step0": ["IFT", 21, 41],
                "step1": ["IFT", 20, 22],
            },
        },
    }

    def _setup(self, tmp_path, env, workflow, files="100-101"):
        cfg_path = _make_config(tmp_path, env, workflow, files=files)
        config   = AlignmentConfig(cfg_path)
        manager  = DAGManager(config)
        manager.create_data_dirs()
        manager.create_dag_dirs()
        import shutil as _shutil
        _shutil.copy(config.tpl_recoexe,  config.dag_recoexe)
        _shutil.copy(config.tpl_milleexe, config.dag_milleexe)
        return config, manager

    def test_mille_sub_count_two_steps(self, tmp_path, env):
        config, manager = self._setup(tmp_path, env, self.WORKFLOW_2STEPS)
        manager.create_mille_submit_files()
        # 2 iterations × 2 steps = 4 mille submit files
        sub_files = list(config.dag_dir.rglob("millepede_iter*.sub"))
        assert len(sub_files) == 4

    def test_mille_sub_fix_rules_in_arguments(self, tmp_path, env):
        config, manager = self._setup(tmp_path, env, self.WORKFLOW_2STEPS)
        manager.create_mille_submit_files()

        sub0 = config.dag_millesub(0, "step0")
        content = sub0.read_text()
        # fix_rules for step0 → "IFT,21,41"
        assert "IFT,21,41" in content

    def test_mille_sub_to_next_iter_false_for_nonfinal_step(self, tmp_path, env):
        config, manager = self._setup(tmp_path, env, self.WORKFLOW_2STEPS)
        manager.create_mille_submit_files()

        # step0 of iter 0 → not final → to_next_iter=False
        content = config.dag_millesub(0, "step0").read_text()
        assert "False" in content

    def test_mille_sub_to_next_iter_true_for_final_step(self, tmp_path, env):
        config, manager = self._setup(tmp_path, env, self.WORKFLOW_2STEPS)
        manager.create_mille_submit_files()

        # step1 of iter 0 is the final step → to_next_iter=True (iter 1 follows)
        content = config.dag_millesub(0, "step1").read_text()
        assert "True" in content

    def test_mille_sub_last_iter_final_step_false(self, tmp_path, env):
        config, manager = self._setup(tmp_path, env, self.WORKFLOW_2STEPS)
        manager.create_mille_submit_files()

        # step1 of iter 1 (last iter) → no next iter → to_next_iter=False
        content = config.dag_millesub(1, "step1").read_text()
        assert "False" in content


# ===========================================================================
# 5. DAGManager — DAG file structure
# ===========================================================================

class TestDagFile:
    WORKFLOW_3SETS = {
        "set0": {"iters": 2, "pede": {"step0": ["IFT", 21, 41],
                                       "step1": ["IFT", 20, 22]}},
        "set1": {"iters": 2, "pede": {"step0": ["side", "3ST"]}},
        "set2": {"iters": 2, "pede": {"step0": ["layer", "3ST"]}},
    }

    def _build_dag(self, tmp_path, env, workflow=None, files="100-102"):
        if workflow is None:
            workflow = self.WORKFLOW_3SETS
        cfg_path = _make_config(tmp_path, env, workflow, files=files)
        config   = AlignmentConfig(cfg_path)
        manager  = DAGManager(config)
        manager.create_data_dirs()
        manager.create_dag_dirs()
        import shutil as _shutil
        _shutil.copy(config.tpl_recoexe,  config.dag_recoexe)
        _shutil.copy(config.tpl_milleexe, config.dag_milleexe)
        manager.create_reco_submit_files()
        manager.create_mille_submit_files()
        dag_path = manager.create_dag_file()
        return dag_path.read_text(), config

    def test_dag_has_one_reco_job_per_iteration(self, tmp_path, env):
        content, config = self._build_dag(tmp_path, env)
        total = config.iters  # 6
        reco_jobs = [line for line in content.splitlines()
                     if line.startswith("JOB reco_iter")]
        assert len(reco_jobs) == total

    def test_dag_reco_job_names_no_file(self, tmp_path, env):
        """Job names for reco must NOT contain a file number."""
        content, _ = self._build_dag(tmp_path, env)
        for line in content.splitlines():
            if line.startswith("JOB reco_iter"):
                job_name = line.split()[1]
                # old format had file numbers like 00100; new format has none
                parts = job_name.split("_")
                assert len(parts) == 2, (
                    f"Reco job name should be 'reco_iterNN', got: {job_name}"
                )

    def test_dag_mille_steps_per_iteration(self, tmp_path, env):
        content, config = self._build_dag(tmp_path, env)
        # set0: 2 steps × 2 iters = 4; set1/set2: 1 step × 2 iters each = 4
        mille_jobs = [line for line in content.splitlines()
                      if line.startswith("JOB millepede_iter")]
        assert len(mille_jobs) == 8  # 4 + 2 + 2

    def test_dag_reco_parent_of_first_mille_step(self, tmp_path, env):
        """reco_iter00 must be the parent of millepede_iter00_step0."""
        content, _ = self._build_dag(tmp_path, env)
        assert "PARENT reco_iter00 CHILD millepede_iter00_step0" in content

    def test_dag_mille_step0_parent_of_step1(self, tmp_path, env):
        content, _ = self._build_dag(tmp_path, env)
        assert "PARENT millepede_iter00_step0 CHILD millepede_iter00_step1" in content

    def test_dag_last_mille_step_parent_of_next_reco(self, tmp_path, env):
        content, _ = self._build_dag(tmp_path, env)
        # set0 has step0 and step1; iter00's step1 must precede iter01's reco
        assert "PARENT millepede_iter00_step1 CHILD reco_iter01" in content

    def test_dag_cross_set_dependency(self, tmp_path, env):
        """Last iter of set0 (step1) must precede first reco of set1."""
        content, _ = self._build_dag(tmp_path, env)
        # set0: iters 0-1; set1: iters 2-3
        # iter01 last mille (step1) → iter02 reco
        assert "PARENT millepede_iter01_step1 CHILD reco_iter02" in content

    def test_dag_retry_settings_present(self, tmp_path, env):
        content, config = self._build_dag(tmp_path, env)
        assert "RETRY reco_iter00 2" in content
        assert "RETRY millepede_iter00_step0 1" in content

    def test_dag_single_set_single_step(self, tmp_path, env):
        """Regression: single-set, single-step workflow (old behaviour)."""
        wf = {"set0": {"iters": 3, "pede": {"step0": []}}}
        content, config = self._build_dag(tmp_path, env, workflow=wf)
        assert config.iters == 3
        assert "PARENT reco_iter00 CHILD millepede_iter00_step0" in content
        assert "PARENT millepede_iter00_step0 CHILD reco_iter01" in content


# ===========================================================================
# Run directly
# ===========================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
