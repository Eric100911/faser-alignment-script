# HTCondor submit file for reconstruction jobs (iteration {iter})
universe = vanilla
executable = {exe_path}

output = {logs_dir}/reco_iter{iter}_$(file_str).out
error  = {logs_dir}/reco_iter{iter}_$(file_str).err
log    = {log_path}

request_cpus = 2
request_memory = 4 GB
request_disk = 8 GB
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
transfer_output_files = logs/

+JobFlavour = "workday"
on_exit_remove = (ExitBySignal == False) && (ExitCode == 0)
max_retries = 3
requirements = (Machine =!= LastRemoteHost) && (OpSysAndVer =?= "AlmaLinux9")

arguments = {year} {run} {stations} $(file_str) {reco_dir} {kfalign_dir} {src_dir} {calypso_asetup} {calypso_setup}
queue file_str from (
{file_list})
