# Migration Guide: From Daemon to DAGman

This guide helps users transition from the old daemon-based approach (`auto_iter.py`) to the new HTCondor DAGman-based approach (`dag_manager.py`).

## Why Migrate?

The daemon approach using `auto_iter.py` with `nohup` is **not officially supported** on CERN lxplus. HTCondor DAGman is the recommended and supported method for managing job workflows.

### Comparison

| Aspect | Daemon (`auto_iter.py`) | DAGman (`dag_manager.py`) |
|--------|------------------------|---------------------------|
| **lxplus Support** | ❌ Unofficial | ✅ Official |
| **Setup Complexity** | Medium | Low (automated) |
| **Job Dependencies** | Manual polling | Automatic |
| **Failure Recovery** | Script-based | Built-in retry + rescue DAGs |
| **Monitoring** | Custom logs | Standard HTCondor tools |
| **Resource Usage** | Persistent daemon | No persistent process |
| **Scalability** | Limited | Excellent |

## Migration Steps

### Prerequisites

Before migrating, ensure you have:
- [ ] Access to CERN lxplus
- [ ] Calypso installed and accessible
- [ ] Pede installed (see installation instructions below)
- [ ] Sufficient storage quota (AFS: ~500MB, EOS: ~25GB for 10 iterations)
- [ ] Stopped any running `auto_iter.py` daemon processes

**Check for running daemons:**
```bash
# Find any auto_iter.py processes
ps aux | grep auto_iter.py

# If found, note the PID and stop it:
kill <pid>

# Verify it's stopped
ps aux | grep auto_iter.py
```

### Step 1: Initial Setup

**1.1 Create configuration file:**

```bash
# Method 1: Interactive setup (recommended for first-time users)
bash setup_config.sh
# Follow the prompts to enter your paths

# Method 2: Manual setup (for experienced users)
python3 config.py
# Then edit config.json with your paths
nano config.json
```

**1.2 Verify configuration:**

```bash
# Validate paths and settings
python3 -c "from config import AlignmentConfig; c = AlignmentConfig(); c.validate_paths()"

# Check configuration contents
cat config.json
```

**1.3 Example config.json:**
```json
{
  "paths": {
    "calypso_install": "/afs/cern.ch/user/y/yourusername/calypso/install",
    "pede_install": "/afs/cern.ch/user/y/yourusername/pede",
    "env_script": "reco_condor_env.sh",
    "work_dir": "/afs/cern.ch/user/y/yourusername/alignment-work",
    "eos_output_dir": "/eos/user/y/yourusername/faser-alignment-output"
  },
  "htcondor": {
    "job_flavour": "longlunch",
    "request_cpus": 1,
    "max_retries": 3,
    "requirements": "(Machine =!= LastRemoteHost) && (OpSysAndVer =?= \"AlmaLinux9\")"
  },
  "storage": {
    "use_eos_for_output": true,
    "keep_intermediate_root_files": true,
    "cleanup_reco_temp_files": true
  },
  "alignment": {
    "default_iterations": 10,
    "polling_interval_seconds": 300
  }
}
```

The configuration file replaces hardcoded paths in `auto_iter.py`.

### Step 2: Install/Verify Dependencies

**2.1 Verify Calypso installation:**
```bash
# Check if Calypso is accessible
ls -la /afs/cern.ch/user/y/yourusername/calypso/install/

# Verify setup script exists
ls -la /afs/cern.ch/user/y/yourusername/calypso/install/setup.sh
```

**2.2 Install pede (if not already installed):**
```bash
# Clone pede repository
git clone --depth 1 --branch V04-17-06 \
     https://gitlab.desy.de/claus.kleinwort/millepede-ii.git \
     /afs/cern.ch/user/y/yourusername/pede

# Build pede
cd /afs/cern.ch/user/y/yourusername/pede
make pede

# Test installation
./pede -t
# Should complete successfully with test output

# Return to work directory
cd -
```

**2.3 Compile Mille:**
```bash
cd /afs/cern.ch/user/y/yourusername/faser-alignment-script/millepede
cmake -B build && cmake --build build && cmake --install build
cd -
```

**2.4 Create/verify environment script:**
```bash
# If it doesn't exist, create it:
cat > reco_condor_env.sh << 'EOF'
#!/bin/bash
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh
asetup --input=calypso/asetup.faser Athena,24.0.41
source /afs/cern.ch/user/y/yourusername/calypso/install/setup.sh
export PATH=/afs/cern.ch/user/y/yourusername/pede:$PATH
export LD_LIBRARY_PATH=/afs/cern.ch/user/y/yourusername/pede:$LD_LIBRARY_PATH
EOF

chmod +x reco_condor_env.sh

# Test the environment script
source reco_condor_env.sh
which pede
# Should output: /afs/cern.ch/user/y/yourusername/pede/pede
```

### Step 3: Convert Your Command

Now you can convert your old daemon command to the new DAGman approach.

**Old command:**
```bash
nohup python3 auto_iter.py -y 2023 -r 011705 -f 450-500 -i 10 &>>auto_iter.log &
```

**New command:**
```bash
python3 dag_manager.py -y 2023 -r 011705 -f 450-500 -i 10 --submit
```

**What changed:**
- ❌ Removed `nohup` - No longer needed, DAGman manages the workflow
- ❌ Removed `&>>auto_iter.log &` - DAGman has its own logging
- ✅ Changed script from `auto_iter.py` to `dag_manager.py`
- ✅ Added `--submit` flag - Automatically submits the DAG after generation
- ✅ All other arguments remain the same

**First migration (test run):**
```bash
# Start with a small test to verify everything works
python3 dag_manager.py -y 2023 -r 011705 -f 450-453 -i 2 --submit

# Monitor the test
condor_q -dag

# Check logs
tail -f Y2023_R011705_F450-453/alignment.dag.dagman.out
```

**After successful test:**
```bash
# Run full production workflow
python3 dag_manager.py -y 2023 -r 011705 -f 450-500 -i 10 --submit
```

### Step 4: Command-Line Arguments

All arguments remain the same:

| Old Flag | New Flag | Description |
|----------|----------|-------------|
| `-y`, `--year` | `-y`, `--year` | Year |
| `-r`, `--run` | `-r`, `--run` | Run number |
| `-f`, `--files` | `-f`, `--files` | File range |
| `-i`, `--iterations` | `-i`, `--iterations` | Number of iterations |
| `--fourst` | `--fourst` | 4-station mode |
| `--threest` | `--threest` | 3-station mode |

**New features:**
- `--config`: Specify custom config file
- `--submit`: Automatically submit DAG after generation

### Step 5: Monitor Your Jobs

The monitoring approach is completely different and much more powerful with DAGman.

**Old approach (daemon-based):**
```bash
# Monitor daemon log
tail -f auto_iter.log

# Check if daemon is running
ps aux | grep auto_iter.py

# No structured view of workflow progress
# Manual log parsing required
```

**New approach (DAGman-based):**
```bash
# 1. Check overall job status
condor_q

# Example output:
# -- Schedd: lxplus123.cern.ch : <188.185.123.123:9618?... @ 12/15/23 14:30:21
# OWNER    BATCH_NAME       SUBMITTED   DONE   RUN    IDLE  TOTAL JOB_IDS
# username alignment.dag   12/15 14:28      5      3      2     10 12345.0 ... 12354.0

# 2. View detailed DAG structure and node status
condor_q -dag

# Example output:
# ID       OWNER      DAG_NodeName          STATUS
# 12345.0  username   reco_01_0            DONE
# 12345.1  username   reco_01_1            DONE
# 12345.2  username   reco_01_2            RUNNING
# 12345.3  username   millepede_01         IDLE
# 12345.4  username   reco_02_0            IDLE

# 3. View jobs without batching (detailed view)
condor_q -nobatch

# 4. Monitor DAGman log in real-time
tail -f Y2023_R011705_F450-500/alignment.dag.dagman.out

# 5. Check job history (completed jobs)
condor_history <username> -limit 20

# 6. Check specific job details
condor_q -long <job_id>

# 7. Check only running jobs
condor_q -run

# 8. Check only idle jobs
condor_q -idle
```

**Benefits of new monitoring:**
- ✅ Real-time workflow visualization
- ✅ Clear parent-child job relationships
- ✅ Per-iteration status tracking
- ✅ Built-in HTCondor tools
- ✅ Standard logging format
- ✅ Easy troubleshooting

### Step 6: Handle Issues

**Old approach:**
```bash
# If daemon crashes, restart manually
# Check logs, fix issues, and re-run
```

**New approach:**
```bash
# HTCondor automatically retries failed jobs
# If DAG fails, use rescue DAG
condor_submit_dag Y2023_R011705_F450-500/alignment.dag.rescue001
```

## Directory Structure Comparison

### Old Structure (auto_iter.py)

```
Y2023_R011705_F450-500/
├── iter01/
│   ├── 1reco/
│   ├── 2kfalignment/
│   └── 3millepede/
└── ...
```

### New Structure (dag_manager.py)

```
Y2023_R011705_F450-500/
├── alignment.dag              # Main DAG file (NEW)
├── alignment.dag.dagman.out   # DAGman log (NEW)
├── iter01/
│   ├── pre_reco.sh           # PRE script (NEW)
│   ├── 1reco/
│   │   ├── reco.sub          # Submit file (NEW)
│   │   └── logs/             # Job logs (NEW)
│   ├── 2kfalignment/
│   └── 3millepede/
│       ├── millepede.sub     # Submit file (NEW)
│       └── run_millepede.sh  # Wrapper script (NEW)
└── ...
```

## Key Differences

### 1. Configuration

**Old:** Paths hardcoded in script
```python
env_path = "/eos/home-s/shunlian/Alignment/env.sh"
```

**New:** Paths in config.json
```json
{
  "paths": {
    "env_script": "reco_condor_env.sh"
  }
}
```

### 2. Job Submission

**Old:** Manual submission within daemon loop
```python
subprocess.run(["condor_submit", "-spool", sub_path])
# Then poll for completion
```

**New:** DAG handles submission and dependencies
```python
# DAG automatically manages all job submissions
# No polling needed
```

### 3. Job Dependencies

**Old:** Manual polling with sleep
```python
while True:
    time.sleep(300)
    # Check if jobs are done
```

**New:** Automatic via DAG
```
PARENT reco_01 CHILD millepede_01
PARENT millepede_01 CHILD reco_02
```

### 4. Failure Handling

**Old:** Script exits on failure
```python
if hold_count != 0:
    print("Error: Some jobs are on hold.")
    sys.exit(1)
```

**New:** Automatic retry + rescue DAGs
```
RETRY reco_01 2
RETRY millepede_01 1
# Plus automatic rescue DAG generation
```

## Testing Your Migration

Before migrating production workflows:

```bash
# 1. Run tests to verify setup
bash tests/test_integration.sh

# 2. Test with small dataset
python3 dag_manager.py -y 2023 -r 011705 -f 400-403 -i 2 --submit

# 3. Monitor test run
condor_q -dag

# 4. Verify results
ls -la Y2023_R011705_F400-403/
```

## Common Issues and Solutions

### Issue 1: Configuration Not Found

**Error:** `FileNotFoundError: Configuration file not found: config.json`

**Solution:**
```bash
python3 config.py
# Edit config.json with your paths
```

### Issue 2: Missing Environment Script

**Error:** Environment script not found

**Solution:**
```bash
# Ensure your config.json points to correct env_script
# The script will use this for job execution
```

### Issue 3: Old Daemon Still Running

**Warning:** If old daemon is still running, stop it first

```bash
# Find daemon process
ps aux | grep auto_iter.py

# Kill daemon
kill <pid>

# Verify it's stopped
ps aux | grep auto_iter.py
```

## FAQs

**Q: Can I still use auto_iter.py?**
A: Yes, but it's not recommended. DAGman is the officially supported approach on lxplus.

**Q: Will my existing workflows be affected?**
A: No, existing completed workflows are not affected. Only new workflows should use DAGman.

**Q: Do I need to change my code?**
A: No code changes needed. Just switch the command and use configuration file.

**Q: What happens if I have an old daemon running?**
A: Stop it first to avoid conflicts. DAGman is self-contained and doesn't need a daemon.

**Q: Can I resume a failed workflow?**
A: Yes! DAGman creates rescue DAGs automatically:
```bash
condor_submit_dag Y2023_R011705_F450-500/alignment.dag.rescue001
```

**Q: How do I monitor multiple DAG workflows?**
A: Use standard HTCondor commands:
```bash
condor_q                  # All your jobs
condor_q -dag            # DAG structure
condor_q -nobatch        # Detailed view
```

## Getting Help

1. **Documentation:**
   - [README.md](README.md) - Overview
   - [USAGE_GUIDE.md](USAGE_GUIDE.md) - Detailed usage
   - [tests/README.md](tests/README.md) - Testing

2. **Test First:**
   ```bash
   bash tests/test_integration.sh
   ```

3. **Check Logs:**
   - DAGman log: `alignment.dag.dagman.out`
   - Job logs: `iter*/1reco/logs/`

4. **HTCondor Resources:**
   - [HTCondor Documentation](https://htcondor.readthedocs.io/)
   - [DAGMan Guide](https://htcondor.readthedocs.io/en/latest/users-manual/dagman-workflows.html)

## Summary

**Migration is straightforward:**
1. ✅ Setup configuration: `bash setup_config.sh`
2. ✅ Replace command: `dag_manager.py` instead of `auto_iter.py`
3. ✅ Monitor with: `condor_q -dag`

**Benefits:**
- ✅ Officially supported
- ✅ Better reliability
- ✅ Easier monitoring
- ✅ Automatic recovery
- ✅ No daemon needed

The new DAGman approach provides a more robust, maintainable, and officially supported solution for FASER alignment workflows.
