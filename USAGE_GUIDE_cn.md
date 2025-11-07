# FASER 对齐 DAGman 使用指南

本指南提供使用基于 HTCondor DAGman 的对齐工作流的分步说明。

## 快速开始

### 1. 初始设置

首先，配置您的环境：

```bash
# 克隆仓库（如果尚未完成）
git clone https://github.com/Eric100911/faser-alignment-script.git
cd faser-alignment-script

# 创建配置文件
python3 config.py

# 编辑 config.json 设置您的路径
nano config.json
```

示例 `config.json`：

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

### 2. 生成并提交 DAG

**小型测试运行（2次迭代，3个文件）：**

```bash
python3 dag_manager.py \
  --year 2023 \
  --run 011705 \
  --files 400-403 \
  --iterations 2 \
  --submit
```

**生产运行（10次迭代，50个文件）：**

```bash
python3 dag_manager.py \
  --year 2023 \
  --run 011705 \
  --files 400-450 \
  --iterations 10 \
  --submit
```

**使用4站模式：**

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400-450 \
  -i 10 \
  --fourst \
  --submit
```

### 3. 监控进度

```bash
# 检查整体状态
condor_q

# 查看 DAG 结构和状态
condor_q -dag

# 检查特定 DAG
condor_q -nobatch

# 实时监控 DAGman 日志
tail -f Y2023_R011705_F400-450/alignment.dag.dagman.out

# 检查作业历史
condor_history <username>
```

### 4. 处理问题

**如果某些作业失败：**

HTCondor 将根据配置的策略自动重试失败的作业（默认：3 次重试）。检查日志以识别根本原因：

```bash
# 导航到日志目录
cd Y2023_R011705_F400-450/iter01/1reco/logs/

# 检查特定作业的错误输出
less reco_0.err

# 搜索常见错误模式
grep -i "error\|fail\|exception" reco_*.err

# 检查作业完成状态
grep -i "exit" reco_*.log
```

**常见失败场景和解决方案：**

1. **找不到原始文件：**
   ```
   Error: Cannot access /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
   ```
   **解决方案：** 验证原始文件存在：
   ```bash
   ls -l /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
   ```

2. **环境设置失败：**
   ```
   Error: asetup: command not found
   ```
   **解决方案：** 检查 config.json 中的环境脚本路径并验证 CVMFS 可访问

3. **数据库复制失败：**
   ```
   Error: Failed to copy ALLP200.db
   ```
   **解决方案：** 确保执行节点上有足够的本地磁盘空间（数据库约 100MB）

**如果 DAG 失败：**

HTCondor 在 DAG 遇到错误时会自动创建挽救 DAG：

```bash
# 检查 DAG 状态
tail Y2023_R011705_F400-450/alignment.dag.dagman.out

# 如果创建了挽救 DAG，提交它以继续
condor_submit_dag Y2023_R011705_F400-450/alignment.dag.rescue001

# 如果有多次挽救尝试，使用最高的数字
condor_submit_dag Y2023_R011705_F400-450/alignment.dag.rescue002
```

**删除正在运行的 DAG：**

```bash
# 查找 DAGman 作业 ID
condor_q -dag

# 删除整个 DAG 工作流
condor_rm <DAGman_job_id>

# 这也将删除与 DAG 关联的所有子作业
```

**从头开始重启：**

```bash
# 删除现有工作流目录
rm -rf Y2023_R011705_F400-450/

# 重新生成并提交新 DAG
python3 dag_manager.py -y 2023 -r 011705 -f 400-450 -i 10 --submit
```

## 高级用法

### 自定义配置文件

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400-450 \
  -i 10 \
  --config my_custom_config.json \
  --submit
```

### 生成 DAG 但不提交

用于在提交前查看 DAG：

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400-450 \
  -i 10

# 查看生成的 DAG
cat Y2023_R011705_F400-450/alignment.dag

# 准备好后手动提交
condor_submit_dag Y2023_R011705_F400-450/alignment.dag
```

### 单文件处理

```bash
python3 dag_manager.py \
  -y 2023 \
  -r 011705 \
  -f 400 \
  -i 5 \
  --submit
```

### 不同的文件范围格式

所有这些都是等效的：

```bash
# 使用破折号
python3 dag_manager.py -y 2023 -r 011705 -f 400-450 -i 10

# 使用冒号
python3 dag_manager.py -y 2023 -r 011705 -f 400:450 -i 10
```

## 理解输出

### 目录结构

提交后，您将拥有：

```
Y2023_R011705_F400-450/
├── alignment.dag              # 主 DAG 文件
├── alignment.dag.dagman.out   # DAGman 执行日志
├── alignment.dag.dagman.log   # DAGman 状态日志
├── alignment.dag.lib.out      # DAGman 库输出
├── alignment.dag.lib.err      # DAGman 库错误
├── iter01/
│   ├── pre_reco.sh           # PRE 脚本（迭代 > 1）
│   ├── 1reco/
│   │   ├── reco.sub          # 重建提交文件
│   │   ├── inputforalign.txt # 对齐常数
│   │   ├── runAlignment.sh   # 复制的可执行文件
│   │   ├── logs/             # 作业日志
│   │   │   ├── reco_0.out
│   │   │   ├── reco_0.err
│   │   │   └── reco_0.log
│   │   └── <run>/<file>/     # 每个文件的工作目录
│   ├── 2kfalignment/         # KF 对齐输出
│   │   └── kfalignment_*.root
│   └── 3millepede/
│       ├── millepede.sub     # Millepede 提交文件
│       ├── run_millepede.sh  # Millepede 包装器
│       ├── millepede.out
│       ├── millepede.err
│       └── millepede.log
├── iter02/
│   └── ...
└── ...
```

### 要检查的日志文件

1. **DAGman 日志**：`alignment.dag.dagman.out` - 显示整体工作流进度
2. **重建日志**：`iter*/1reco/logs/reco_*.err` - 单个作业错误
3. **Millepede 日志**：`iter*/3millepede/millepede.out` - 对齐计算输出

## 监控示例

### 检查有多少作业正在运行

```bash
condor_q -run | grep <username>
```

### 检查有多少作业处于空闲状态

```bash
condor_q -idle | grep <username>
```

### 检查已完成的作业

```bash
condor_history <username> -limit 10
```

### 查看 DAG 进度

```bash
# 这显示父子关系
condor_q -dag

# 示例输出：
# ID      OWNER      DAG_NodeName          STATUS
# 12345.0 username   reco_01              DONE
# 12345.1 username   millepede_01         DONE
# 12345.2 username   reco_02              RUNNING
# 12345.3 username   millepede_02         IDLE
```

## 故障排除

### 问题：找不到环境脚本

**错误**：`FileNotFoundError: Environment script not found: reco_condor_env.sh`

**解决方案**：如果您在首次运行 `main.py` 时提供 `--calypso_path`，环境脚本将自动创建，或者您可以手动创建。

**手动创建：**
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

### 问题：找不到配置文件

**错误**：`FileNotFoundError: Configuration file not found: config.json`

**解决方案**：
```bash
# 交互式配置（推荐）
bash setup_config.sh

# 或手动配置
python3 config.py
# 然后编辑生成的 config.json 设置您的路径
nano config.json
```

**创建后验证配置：**
```bash
python3 -c "from config import AlignmentConfig; c = AlignmentConfig(); c.validate_paths()"
```

### 问题：作业卡在空闲状态

**可能原因**：
1. 未满足要求（例如，AlmaLinux9 不可用）
2. 达到资源限制（配额、槽位可用性）
3. 会计组问题
4. 网络或系统问题

**诊断和解决方案：**
```bash
# 检查作业为何处于空闲状态
condor_q -better-analyze <job_id>

# 检查作业要求
condor_q -long <job_id> | grep Requirements

# 检查可用资源
condor_status -compact

# 如果 AlmaLinux9 不可用，修改 config.json 中的要求：
# "requirements": "(Machine =!= LastRemoteHost)"

# 检查会计组
condor_q -long <job_id> | grep AccountingGroup
```

### 问题：作业失败并显示"找不到原始文件"

**日志中的错误**：
```
FileNotFoundError: /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
```

**解决方案**：验证原始数据文件存在且可访问：

```bash
# 检查文件是否存在
ls -l /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw

# 检查 EOS 挂载点
df -h | grep eos

# 如果文件缺失，验证运行编号和文件编号：
ls /eos/experiment/faser/raw/2023/011705/

# 检查权限
eos fileinfo /eos/experiment/faser/raw/2023/011705/Faser-Physics-011705-00400.raw
```

### 问题：Millepede 失败

**检查日志**：
```bash
cd Y2023_R011705_F400-450/iter01/3millepede/
cat millepede.err
cat millepede.out
```

**常见问题**：

1. **PATH 中缺少 pede**
   ```
   Error: pede: command not found
   ```
   **解决方案：**
   ```bash
   # 验证 pede 安装
   which pede
   
   # 如果缺失，添加到环境脚本
   echo 'export PATH=/path/to/pede:$PATH' >> reco_condor_env.sh
   echo 'export LD_LIBRARY_PATH=/path/to/pede:$LD_LIBRARY_PATH' >> reco_condor_env.sh
   ```

2. **重建中没有根文件**
   ```
   Error: No input files found
   ```
   **解决方案：**
   ```bash
   # 检查重建是否产生输出
   ls Y2023_R011705_F400-450/iter01/2kfalignment/
   
   # 如果为空，检查重建作业日志
   cat Y2023_R011705_F400-450/iter01/1reco/logs/reco_*.err
   ```

3. **内存不足**
   ```
   Error: std::bad_alloc
   ```
   **解决方案：** 在 config.json 中增加内存请求：
   ```json
   {
     "htcondor": {
       "request_memory": "4GB"
     }
   }
   ```

### 问题：输出文件不在预期位置

**问题**：作业成功完成后找不到输出文件

**解决方案**：检查存储配置：

```bash
# 检查 config.json 中的输出路径
grep -A 5 '"storage"' config.json
grep -A 5 '"paths"' config.json

# 验证 EOS 目录存在
ls -la /eos/user/y/yourusername/faser-alignment-output/

# 检查工作目录中的符号链接
ls -la Y2023_R011705_F400-450/iter01/

# 如果使用 EOS，检查文件是否在那里
eos ls /eos/user/y/yourusername/faser-alignment-output/Y2023_R011705_F400-450/iter01/2kfalignment/
```

### 问题：AFS 配额超限

**错误**：`Disk quota exceeded`

**当前状态**：当前实现中不应发生这种情况，因为作业在执行节点本地存储上运行。

**如果仍然发生：**
```bash
# 检查 AFS 配额
fs quota ~

# 识别大目录
du -h --max-depth=1 . | sort -hr | head -10

# 清理旧工作流
rm -rf Y2023_R011705_F400-450/

# 验证 EOS 已配置用于输出
grep eos_output_dir config.json

# 在 config.json 中启用清理
"cleanup_reco_temp_files": true
```

### 问题：权限被拒绝错误

**错误**：访问文件或目录时 `Permission denied`

**解决方案：**
```bash
# 检查文件权限
ls -la /path/to/file

# 对于 EOS 文件，检查所有权
eos fileinfo /eos/user/y/yourusername/file

# 在 EOS 上设置适当的权限
eos chmod 755 /eos/user/y/yourusername/faser-alignment-output/

# 对于 AFS，检查 ACL
fs listacl /afs/cern.ch/user/y/yourusername/alignment-work/
```

### 问题：HTCondor 作业保持在 "Held" 状态

**问题**：作业被保持且未执行

**诊断：**
```bash
# 检查保持原因
condor_q -hold <job_id>

# 获取详细的保持原因
condor_q -long <job_id> | grep HoldReason
```

**常见保持原因的解决方案：**

1. **文件传输失败**
   - 检查网络连接
   - 验证输入文件存在
   - 检查文件权限

2. **内存超限**
   - 在 config.json 中增加内存请求

3. **磁盘空间超限**
   - 清理旧文件
   - 对大输出使用 EOS

**释放被保持的作业：**
```bash
condor_release <job_id>
```

## 性能提示

1. **选择适当的作业风格**：
   - `espresso`：< 20分钟（用于测试）
   - `microcentury`：< 1小时
   - `longlunch`：< 2小时（默认）
   - `workday`：< 8小时
   - `tomorrow`：< 1天

2. **优化文件范围**：
   - 从小范围开始测试（3-5个文件）
   - 验证后扩大规模（50-100个文件）

3. **监控资源使用**：
   ```bash
   condor_q -l <job_id> | grep -E "Memory|Cpus|Disk"
   ```

## 从守护进程方法迁移

如果您从旧的 `auto_iter.py` 守护进程方法迁移：

**旧命令**：
```bash
nohup python3 auto_iter.py -y 2023 -r 011705 -f 450-500 -i 10 &>>auto_iter.log &
```

**新命令**：
```bash
python3 dag_manager.py -y 2023 -r 011705 -f 450-500 -i 10 --submit
```

**好处**：
- ✅ 无需 `nohup` 或后台进程
- ✅ 自动作业依赖管理
- ✅ 内置重试逻辑
- ✅ 使用标准 HTCondor 工具更好地监控
- ✅ 在 lxplus 上官方支持

## 获取帮助

遇到问题或疑问：

1. 检查日志（DAGman 和特定作业）
2. 查看本指南和 README.md
3. 运行测试套件：`bash tests/test_integration.sh`
4. 查看 HTCondor 文档：https://htcondor.readthedocs.io/
5. 联系开发团队

## 运行测试

在生产使用前，验证一切正常：

```bash
# 运行单元测试
python3 tests/test_config.py -v
python3 tests/test_dag_generation.py -v

# 运行集成测试
bash tests/test_integration.sh
```

所有测试都应在继续生产工作流之前通过。
