# FASER Alignment DAGman Usage Guide

This guide provides step-by-step instructions for using the HTCondor DAGman-based alignment workflow.

## Quick Start

### 1. Initial Setup

First, configure your environment:

```bash
# Clone the repository (if not already done)
git clone https://github.com/Eric100911/faser-alignment-script.git
cd faser-alignment-script

# Create configuration file
python3 config.py

# Edit config.json with your paths
nano config.json
```

Example `config.json`:

```json
{
  "paths": {
    "calypso_install": "/afs/cern.ch/user/y/yourusername/calypso/install",
    "pede_install": "/afs/cern.ch/user/y/yourusername/pede",
    "env_script": "reco_condor_env.sh"
  },
  "htcondor": {
    "job_flavour": "longlunch",
    "request_cpus": 1,
    "max_retries": 3,
    "requirements": "(Machine =!= LastRemoteHost) && (OpSysAndVer =?= \"AlmaLinux9\")"
  },
  "alignment": {
    "default_iterations": 10,
    "polling_interval_seconds": 300
  }
}
```

### 2. Generate and Submit DAG

**For a small test run (2 iterations, 3 files):**

```bash
python3 dag_manager.py \
  --year 2023 \
  --run 011705 \
  --files 400-403 \
  --iterations 2 \
  --submit
```

**For a production run (10 iterations, 50 files):**

```bash
python3 dag_manager.py \
  --year 2023 \
  --run 011705 \
  --files 400-450 \
  --iterations 10 \
  --submit
```

**With 4-station mode:**

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400-450 \
  -i 10 \
  --fourst \
  --submit
```

### 3. Monitor Progress

```bash
# Check overall status
condor_q

# View DAG structure and status
condor_q -dag

# Check specific DAG
condor_q -nobatch

# Monitor DAGman log in real-time
tail -f Y2023_R011705_F400-450/alignment.dag.dagman.out

# Check job history
condor_history <username>
```

### Step 4: Handle Issues

**If some jobs fail:**

HTCondor will automatically retry failed jobs according to the configured policy (default: 3 retries). Check the logs to identify the root cause:

```bash
# Navigate to the logs directory
cd Y2023_R011705_F400-450/iter01/1reco/logs/

# Check error output for a specific job
less reco_0.err

# Search for common error patterns
grep -i "error\|fail\|exception" reco_*.err

# Check job completion status
grep -i "exit" reco_*.log
```

**Common failure scenarios and solutions:**

1. **Raw file not found:**
   ```
   Error: Cannot access /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
   ```
   **Solution:** Verify raw file exists:
   ```bash
   ls -l /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
   ```

2. **Environment setup failure:**
   ```
   Error: asetup: command not found
   ```
   **Solution:** Check environment script path in config.json and verify CVMFS is accessible

3. **Database copy failure:**
   ```
   Error: Failed to copy ALLP200.db
   ```
   **Solution:** Ensure sufficient local disk space on execute node (database is ~100MB)

**If the DAG fails:**

HTCondor creates rescue DAGs automatically when a DAG encounters errors:

```bash
# Check DAG status
tail Y2023_R011705_F400-450/alignment.dag.dagman.out

# If rescue DAG was created, submit it to continue
condor_submit_dag Y2023_R011705_F400-450/alignment.dag.rescue001

# If multiple rescue attempts, use the highest number
condor_submit_dag Y2023_R011705_F400-450/alignment.dag.rescue002
```

**To remove a running DAG:**

```bash
# Find the DAGman job ID
condor_q -dag

# Remove the entire DAG workflow
condor_rm <DAGman_job_id>

# This will also remove all child jobs associated with the DAG
```

**To restart from scratch:**

```bash
# Remove existing workflow directory
rm -rf Y2023_R011705_F400-450/

# Regenerate and submit fresh DAG
python3 dag_manager.py -y 2023 -r 011705 -f 400-450 -i 10 --submit
```

## Advanced Usage

### Custom Configuration File

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400-450 \
  -i 10 \
  --config my_custom_config.json \
  --submit
```

### Generate DAG Without Submitting

Useful for reviewing the DAG before submission:

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400-450 \
  -i 10

# Review the generated DAG
cat Y2023_R011705_F400-450/alignment.dag

# Submit manually when ready
condor_submit_dag Y2023_R011705_F400-450/alignment.dag
```

### Single File Processing

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400 \
  -i 5 \
  --submit
```

### Different File Range Formats

All of these are equivalent:

```bash
# Using dash
python3 dag_manager.py -y 2023 -r 011705 -f 400-450 -i 10

# Using colon
python3 dag_manager.py -y 2023 -r 011705 -f 400:450 -i 10
```

## Understanding the Output

### Directory Structure

After submission, you'll have:

```
Y2023_R011705_F400-450/
├── alignment.dag              # Main DAG file
├── alignment.dag.dagman.out   # DAGman execution log
├── alignment.dag.dagman.log   # DAGman status log
├── alignment.dag.lib.out      # DAGman library output
├── alignment.dag.lib.err      # DAGman library errors
├── iter01/
│   ├── pre_reco.sh           # PRE script (for iter > 1)
│   ├── 1reco/
│   │   ├── reco.sub          # Reconstruction submit file
│   │   ├── inputforalign.txt # Alignment constants
│   │   ├── runAlignment.sh   # Copied executable
│   │   ├── logs/             # Job logs
│   │   │   ├── reco_0.out
│   │   │   ├── reco_0.err
│   │   │   └── reco_0.log
│   │   └── <run>/<file>/     # Per-file work directories
│   ├── 2kfalignment/         # KF alignment output
│   │   └── kfalignment_*.root
│   └── 3millepede/
│       ├── millepede.sub     # Millepede submit file
│       ├── run_millepede.sh  # Millepede wrapper
│       ├── millepede.out
│       ├── millepede.err
│       └── millepede.log
├── iter02/
│   └── ...
└── ...
```

### Log Files to Check

1. **DAGman logs**: `alignment.dag.dagman.out` - Shows overall workflow progress
2. **Reconstruction logs**: `iter*/1reco/logs/reco_*.err` - Individual job errors
3. **Millepede logs**: `iter*/3millepede/millepede.out` - Alignment computation output

## Monitoring Examples

### Check How Many Jobs Are Running

```bash
condor_q -run | grep <username>
```

### Check How Many Jobs Are Idle

```bash
condor_q -idle | grep <username>
```

### Check Completed Jobs

```bash
condor_history <username> -limit 10
```

### See DAG Progress

```bash
# This shows parent-child relationships
condor_q -dag

# Example output:
# ID      OWNER      DAG_NodeName          STATUS
# 12345.0 username   reco_01              DONE
# 12345.1 username   millepede_01         DONE
# 12345.2 username   reco_02              RUNNING
# 12345.3 username   millepede_02         IDLE
```

## Troubleshooting

### Problem: Environment script not found

**Error**: `FileNotFoundError: Environment script not found: reco_condor_env.sh`

**Solution**: The environment script will be created automatically if you provide the `--calypso_path` when first running `main.py`, or you can create it manually.

**Manual creation:**
```bash
cat > reco_condor_env.sh << 'EOF'
#!/bin/bash
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh
asetup --input=calypso/asetup.faser Athena,24.0.41
source /path/to/your/calypso/install/setup.sh
export PATH=/path/to/your/pede:$PATH
export LD_LIBRARY_PATH=/path/to/your/pede:$LD_LIBRARY_PATH
EOF

chmod +x reco_condor_env.sh
```

### Problem: Config file not found

**Error**: `FileNotFoundError: Configuration file not found: config.json`

**Solution**: 
```bash
# Interactive configuration (recommended)
bash setup_config.sh

# Or manual configuration
python3 config.py
# Then edit the generated config.json with your paths
nano config.json
```

**Verify configuration after creation:**
```bash
python3 -c "from config import AlignmentConfig; c = AlignmentConfig(); c.validate_paths()"
```

### Problem: Jobs stuck in idle state

**Possible causes**:
1. Requirements not met (e.g., AlmaLinux9 not available)
2. Resource limits reached (quota, slot availability)
3. Accounting group issues
4. Network or system issues

**Diagnosis and solutions:**
```bash
# Check why jobs are idle
condor_q -better-analyze <job_id>

# Check job requirements
condor_q -long <job_id> | grep Requirements

# Check available resources
condor_status -compact

# If AlmaLinux9 is not available, modify requirements in config.json:
# "requirements": "(Machine =!= LastRemoteHost)"

# Check accounting group
condor_q -long <job_id> | grep AccountingGroup
```

### Problem: Jobs fail with "Cannot find raw file"

**Error in logs**: 
```
FileNotFoundError: /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
```

**Solution**: Verify the raw data files exist and are accessible:

```bash
# Check if file exists
ls -l /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw

# Check EOS mount point
df -h | grep eos

# If file missing, verify run number and file number:
ls /eos/experiment/faser/raw/2023/011705/

# Check permissions
eos fileinfo /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
```

### Problem: Millepede fails

**Check logs**:
```bash
cd Y2023_R011705_F400-450/iter01/3millepede/
cat millepede.err
cat millepede.out
```

**Common issues**:

1. **Missing pede in PATH**
   ```
   Error: pede: command not found
   ```
   **Solution:**
   ```bash
   # Verify pede installation
   which pede
   
   # Add to environment script if missing
   echo 'export PATH=/path/to/pede:$PATH' >> reco_condor_env.sh
   echo 'export LD_LIBRARY_PATH=/path/to/pede:$LD_LIBRARY_PATH' >> reco_condor_env.sh
   ```

2. **No root files from reconstruction**
   ```
   Error: No input files found
   ```
   **Solution:**
   ```bash
   # Check if reconstruction produced output
   ls Y2023_R011705_F400-450/iter01/2kfalignment/
   
   # If empty, check reconstruction job logs
   cat Y2023_R011705_F400-450/iter01/1reco/logs/reco_*.err
   ```

3. **Insufficient memory**
   ```
   Error: std::bad_alloc
   ```
   **Solution:** Increase memory request in config.json:
   ```json
   {
     "htcondor": {
       "request_memory": "4GB"
     }
   }
   ```

### Problem: Output files not in expected location

**Issue**: Cannot find output files after successful job completion

**Solution**: Check storage configuration:

```bash
# Check config.json for output paths
grep -A 5 '"storage"' config.json
grep -A 5 '"paths"' config.json

# Verify EOS directory exists
ls -la /eos/user/y/yourusername/faser-alignment-output/

# Check symlinks in work directory
ls -la Y2023_R011705_F400-450/iter01/

# If using EOS, check if files are there
eos ls /eos/user/y/yourusername/faser-alignment-output/Y2023_R011705_F400-450/iter01/2kfalignment/
```

### Problem: AFS quota exceeded

**Error**: `Disk quota exceeded`

**Current status**: This should not occur with the current implementation as jobs run on execute node local storage.

**If it still occurs:**
```bash
# Check AFS quota
fs quota ~

# Identify large directories
du -h --max-depth=1 . | sort -hr | head -10

# Clean up old workflows
rm -rf Y2023_R011705_F400-450/

# Verify EOS is configured for output
grep eos_output_dir config.json

# Enable cleanup in config.json
"cleanup_reco_temp_files": true
```

### Problem: Permission denied errors

**Error**: `Permission denied` when accessing files or directories

**Solutions:**
```bash
# Check file permissions
ls -la /path/to/file

# For EOS files, check ownership
eos fileinfo /eos/user/y/yourusername/file

# Set proper permissions on EOS
eos chmod 755 /eos/user/y/yourusername/faser-alignment-output/

# For AFS, check ACLs
fs listacl /afs/cern.ch/user/y/yourusername/alignment-work/
```

### Problem: HTCondor job remains in "Held" state

**Issue**: Jobs are held and not executing

**Diagnosis:**
```bash
# Check hold reason
condor_q -hold <job_id>

# Get detailed hold reason
condor_q -long <job_id> | grep HoldReason

# Common hold reasons and solutions:
```

**Solutions for common hold reasons:**

1. **Failed to transfer files**
   - Check network connectivity
   - Verify input files exist
   - Check file permissions

2. **Memory exceeded**
   - Increase memory request in config.json

3. **Disk space exceeded**
   - Clean up old files
   - Use EOS for large outputs

**Release held job:**
```bash
condor_release <job_id>
```

## Performance Tips

1. **Choose appropriate job flavour**:
   - `espresso`: < 20 minutes (for testing)
   - `microcentury`: < 1 hour
   - `longlunch`: < 2 hours (default)
   - `workday`: < 8 hours
   - `tomorrow`: < 1 day

2. **Optimize file ranges**:
   - Start with small ranges for testing (3-5 files)
   - Scale up once validated (50-100 files)

3. **Monitor resource usage**:
   ```bash
   condor_q -l <job_id> | grep -E "Memory|Cpus|Disk"
   ```

## Migration from Daemon Approach

If you're migrating from the old `auto_iter.py` daemon approach:

**Old command**:
```bash
nohup python3 auto_iter.py -y 2023 -r 011705 -f 450-500 -i 10 &>>auto_iter.log &
```

**New command**:
```bash
python3 dag_manager.py -y 2023 -r 011705 -f 450-500 -i 10 --submit
```

**Benefits**:
- ✅ No need for `nohup` or background processes
- ✅ Automatic job dependency management
- ✅ Built-in retry logic
- ✅ Better monitoring with standard HTCondor tools
- ✅ Officially supported on lxplus

## Getting Help

For issues or questions:

1. Check the logs (DAGman and job-specific)
2. Review this guide and README.md
3. Run the test suite: `bash tests/test_integration.sh`
4. Check HTCondor documentation: https://htcondor.readthedocs.io/
5. Contact the development team

## Running Tests

Before production use, verify everything works:

```bash
# Run unit tests
python3 tests/test_config.py -v
python3 tests/test_dag_generation.py -v

# Run integration test
bash tests/test_integration.sh
```

All tests should pass before proceeding to production workflows.
