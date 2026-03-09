#!/usr/bin/env python3
"""
HTCondor DAGman manager for FASER alignment workflow.

This module generates and manages HTCondor DAG files for iterative alignment,
replacing the daemon-based approach with a more robust DAGman-based solution.
"""

import argparse
import shutil
from pathlib import Path

from AlignmentConfig import AlignmentConfig
import ColorfulPrint

# Test: python3 dag_manager.py --submit

# TODO: 运行前检查 config.json 中的路径是否存在，以及各种语法合理性
# TODO: 支持断点执行
class DAGManager:
    """Manages HTCondor DAG generation for alignment workflow."""
    
    def __init__(self, config: AlignmentConfig):
        """
        Initialize DAG manager.
        
        Args:
            config: AlignmentConfig instance
        """
        self.config = config
    
    def archive_config(self) -> None:
        """Archive the config file to the data directory."""
        self.config.archive()

    def validate_paths(self) -> None:
        """Validate necessary paths exist."""
        _ = self.config.src_dir
        _ = self.config.tpl_dir
        _ = self.config.tpl_inputforalign
        _ = self.config.tpl_recosub
        _ = self.config.tpl_recoexe
        _ = self.config.tpl_millesub
        _ = self.config.tpl_milleexe
        _ = self.config.env_calypso_asetup
        _ = self.config.env_calypso_setup
        _ = self.config.env_pede
        _ = self.config.env_root

    def create_data_dirs(self) -> None:
        """Create data directories for all iterations."""
        _ = self.config.data_dir
        for it in range(self.config.iters):
            _ = self.config.data_iter_dir(it)
            _ = self.config.reco_dir(it)
            _ = self.config.kfalign_dir(it)
            _ = self.config.millepede_dir(it)
    
    def create_dag_dirs(self) -> None:
        """Create DAG working directories for all iterations."""
        _ = self.config.dag_dir
        for it in range(self.config.iters):
            _ = self.config.dag_iter_dir(it)
            _ = self.config.logs_dir(it)
    
    def copy_first_inputforalign(self) -> None:
        initial = self.config.data_initial
        if initial.exists():
            ColorfulPrint.print_yellow(f"Warning: ")
            print(f"Overwritting initial inputforalign file: {initial}")
        shutil.copy(self.config.tpl_inputforalign, initial)
    
    def create_reco_exe_files(self) -> None:
        """Create reco executable script in DAG directory."""
        dag_recoexe = self.config.dag_recoexe
        if dag_recoexe.exists():
            ColorfulPrint.print_yellow(f"Warning: ")
            print(f"Overwritting reco executable: {dag_recoexe}")
        shutil.copy(self.config.tpl_recoexe, dag_recoexe)
    
    def create_reco_submit_files(self) -> None:
        """Create one reco submit file per iteration (file_str injected via DAG VARS)."""
        with open(self.config.tpl_recosub, 'r') as tpl_file:
            tpl_content = tpl_file.read()
        for it in range(self.config.iters):
            iter_str = f"{it:02d}"
            sub_content = tpl_content.format(
                iter=iter_str,
                year=self.config.year,
                run=self.config.run,
                stations=self.config.stations,
                exe_path=self.config.dag_recoexe,
                log_path=self.config.logs_reco_log(it),
                logs_dir=self.config.logs_dir(it),
                reco_dir=self.config.reco_dir(it),
                kfalign_dir=self.config.kfalign_dir(it),
                src_dir=self.config.src_dir,
                calypso_asetup=self.config.env_calypso_asetup,
                calypso_setup=self.config.env_calypso_setup,
            )
            recosub = self.config.dag_recosub(it)
            if recosub.exists():
                ColorfulPrint.print_yellow(f"Warning: ")
                print(f"Overwritting reco submit file: {recosub}")
            with open(recosub, 'w') as sub_file:
                sub_file.write(sub_content)

    def create_mille_exe_files(self) -> None:
        """Create millepede executable script in DAG directory."""
        dag_milleexe = self.config.dag_milleexe
        if dag_milleexe.exists():
            ColorfulPrint.print_yellow(f"Warning: ")
            print(f"Overwritting millepede executable: {dag_milleexe}")
        shutil.copy(self.config.tpl_milleexe, dag_milleexe)
    
    def create_mille_submit_files(self) -> None:
        """Create millepede submit files for every workflow step of every iteration."""
        with open(self.config.tpl_millesub, 'r') as tpl_file:
            tpl_content = tpl_file.read()
        total = self.config.iters
        for it in range(total):
            ws, _ = self.config.iter_info(it)
            step_names = list(ws.pede_steps.keys())
            for step_idx, step_name in enumerate(step_names):
                is_final_step = (step_idx == len(step_names) - 1)
                # Only the final step within an iteration feeds the next reco
                to_next = is_final_step and (it < total - 1)
                fix_items = ws.pede_steps[step_name]
                fix_rules = ",".join(str(x) for x in fix_items)
                sub_content = tpl_content.format(
                    iter=f"{it:02d}",
                    step=step_name,
                    exe_path=self.config.dag_milleexe,
                    out_path=self.config.logs_mille_out(it, step_name),
                    err_path=self.config.logs_mille_err(it, step_name),
                    log_path=self.config.logs_mille_log(it, step_name),
                    to_next_iter=to_next,
                    src_dir=self.config.src_dir,
                    kfalign_dir=self.config.kfalign_dir(it),
                    next_reco_dir=(
                        self.config.reco_dir(it + 1) if to_next else ""
                    ),
                    env_pede=self.config.env_pede,
                    env_root=self.config.env_root,
                    fix_rules=fix_rules,
                )
                millesub = self.config.dag_millesub(it, step_name)
                if millesub.exists():
                    ColorfulPrint.print_yellow(f"Warning: ")
                    print(f"Overwritting millepede submit file: {millesub}")
                with open(millesub, 'w') as sub_file:
                    sub_file.write(sub_content)

    def create_dag_file(self) -> Path:
        """Create DAG file for complete alignment workflow."""
        dag_file = self.config.dag_file
        dag_content = "# HTCondor DAG for FASER alignment workflow\n\n"
        total = self.config.iters
        for it in range(total):
            ws, _ = self.config.iter_info(it)
            step_names = list(ws.pede_steps.keys())

            # ---- reco jobs: one JOB node per file, all sharing the same submit file ----
            # DAGman VARS injects the file_str macro into each node's submit call
            # so that rescue DAGs re-run only the individual file nodes that failed.
            reco_sub = self.config.dag_recosub(it)
            dag_content += f"# Iteration {it} reconstruction jobs\n"
            for file_str in self.config.files:
                reco_job = self.config.dag_recojob(it, file_str)
                dag_content += f"JOB {reco_job} {reco_sub}\n"
                dag_content += f"VARS {reco_job} file_str=\"{file_str}\"\n"

            # ---- millepede steps ----
            dag_content += f"\n# Iteration {it} millepede jobs\n"
            for step_name in step_names:
                mille_sub = self.config.dag_millesub(it, step_name)
                mille_job = self.config.dag_millejob(it, step_name)
                dag_content += f"JOB {mille_job} {mille_sub}\n"

            # ---- dependencies ----
            dag_content += f"\n# Iteration {it} dependencies\n"
            first_mille = self.config.dag_millejob(it, step_names[0])
            # every reco file job → first mille step
            for file_str in self.config.files:
                reco_job = self.config.dag_recojob(it, file_str)
                dag_content += f"PARENT {reco_job} CHILD {first_mille}\n"
            # mille step[k] → mille step[k+1]
            for k in range(len(step_names) - 1):
                parent_j = self.config.dag_millejob(it, step_names[k])
                child_j  = self.config.dag_millejob(it, step_names[k + 1])
                dag_content += f"PARENT {parent_j} CHILD {child_j}\n"
            # previous iteration's last mille → all current reco jobs
            if it != 0:
                prev_ws, _ = self.config.iter_info(it - 1)
                prev_steps = list(prev_ws.pede_steps.keys())
                last_mille = self.config.dag_millejob(it - 1, prev_steps[-1])
                for file_str in self.config.files:
                    reco_job = self.config.dag_recojob(it, file_str)
                    dag_content += f"PARENT {last_mille} CHILD {reco_job}\n"
            dag_content += "\n"

        # Add retry settings
        dag_content += "# Retry settings\n"
        for it in range(total):
            ws, _ = self.config.iter_info(it)
            for file_str in self.config.files:
                reco_job = self.config.dag_recojob(it, file_str)
                dag_content += f"RETRY {reco_job} 2\n"
            for step_name in ws.pede_steps.keys():
                mille_job = self.config.dag_millejob(it, step_name)
                dag_content += f"RETRY {mille_job} 1\n"

        # Write DAG file
        if dag_file.exists():
            ColorfulPrint.print_yellow(f"Warning: ")
            print(f"Overwritting DAG file: {dag_file}")
        with open(dag_file, 'w') as f:
            f.write(dag_content)
        return dag_file



def main():
    """Main entry point for DAG manager."""
    parser = argparse.ArgumentParser(
        description="Generate HTCondor DAG for FASER alignment workflow"
    )
    
    parser.add_argument('--config', type=str, default='config.json',
                        help='Path to configuration file')
    parser.add_argument('--submit', action='store_true', default=False,
                        help='Automatically submit DAG to HTCondor')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = AlignmentConfig(Path(args.config))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please check your configuration file.")
        return 1
    except (TypeError, ValueError) as e:
        print(f"Configuration error: {e}")
        return 1
    
    # Create DAG
    dag_manager = DAGManager(config)
    dag_manager.archive_config()
    dag_manager.validate_paths()
    dag_manager.create_data_dirs()
    dag_manager.create_dag_dirs()
    dag_manager.copy_first_inputforalign()
    dag_manager.create_reco_exe_files()
    dag_manager.create_reco_submit_files()
    dag_manager.create_mille_exe_files()
    dag_manager.create_mille_submit_files()
    dag_path = dag_manager.create_dag_file()
    dag_dir = dag_path.parent
    
    if args.submit:
        import subprocess
        print("\nSubmitting DAG to HTCondor...")
        
        try:
            result = subprocess.run(
                ["condor_submit_dag", str(dag_path)],
                cwd=dag_dir,
                capture_output=True,
                text=True
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"Error submitting DAG: {result.stderr}")
                return 1
        except Exception as e:
            print(f"Exception occurred while submitting DAG: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
