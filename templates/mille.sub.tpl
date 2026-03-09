# HTCondor submit file for Millepede job (iteration {iter}, step {step})
universe = vanilla
executable = {exe_path}

output = {out_path}
error  = {err_path}
log    = {log_path}

request_cpus = 1
request_memory = 2 GB
request_disk = 2 GB
should_transfer_files = YES
when_to_transfer_output = ON_EXIT

+JobFlavour = "workday"
on_exit_remove = (ExitBySignal == False) && (ExitCode == 0)
max_retries = 2

arguments = {to_next_iter} {src_dir} {kfalign_dir} {next_reco_dir} {env_pede} {env_root} {fix_rules}
queue
