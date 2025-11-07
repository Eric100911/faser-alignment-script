# FASER 对齐存储管理指南

本指南说明如何配置和使用 HTCondor DAGman 框架，并正确管理 AFS 和 EOS 存储。

## 存储架构

### AFS vs EOS

**AFS (Andrew File System):**
- 小配额（通常几 GB）
- 适用于：代码、配置文件、提交文件、DAG 文件
- 位置：`/afs/cern.ch/user/`
- 用途：作业提交和工作流管理

**EOS (CERN 磁盘存储):**
- 大配额（数百 GB 到 TB）
- 适用于：大数据文件、中间结果、输出文件
- 位置：`/eos/experiment/faser/` 或 `/eos/user/`
- 用途：Root 文件、对齐输出、重建结果

## HTCondor 执行节点存储

**关键理解**：重建作业现在在 HTCondor 执行节点上运行，使用本地临时空间，**而不是 AFS**。这是防止磁盘配额问题的关键设计特性。

### 执行节点存储的工作原理

当重建作业在 HTCondor 执行节点上启动时：

1. **作业初始化**：HTCondor 在执行节点的本地磁盘上分配临时工作目录
   - 典型位置：`/tmp/` 或 `$_CONDOR_SCRATCH_DIR`
   - 每个作业都有自己的隔离工作空间
   - 作业执行期间不与 AFS 配额交互

2. **数据库文件处理**：
   - `aligndb_copy.sh` 脚本将对齐数据库（约 100MB）复制到执行节点本地磁盘
   - 数据库在重建期间本地使用
   - 此临时副本不占用 AFS 空间
   - 作业完成时数据库被删除

3. **中间文件**：
   - ROOT 文件处理在执行节点的本地磁盘上进行
   - 重建期间创建的临时文件保留在执行节点上
   - 执行节点通常有 10s-100s GB 的临时空间可用

4. **输出文件传输**：
   - 只有最终输出文件（kfalignment_*.root、xAOD_*.root）被传输回来
   - 文件存入 EOS（如果已配置）或 AFS 工作目录
   - 日志文件传输到 AFS 日志目录
   - 小文件，AFS 配额可管理

5. **自动清理**：
   - HTCondor 在作业完成后自动清理执行节点存储
   - 临时文件、数据库副本和临时空间都被删除
   - 不需要手动清理
   - 执行节点上没有持久存储消耗

### 容量和可扩展性

**为什么这个设计很重要：**
- **50+ 并发作业**：可以同时运行而不会出现 AFS 配额问题
- **100MB × 50 = 5GB**：如果存储在 AFS 上，数据库文件将占用 5GB
- **执行节点容量**：通常每个节点有 50-200 GB 的本地临时空间
- **执行期间零 AFS 影响**：作业在重建期间不接触 AFS

**示例场景：**
```
并行运行 50 个重建作业：
- 旧设计（在 AFS 上）：5GB 数据库文件 + 中间文件 = AFS 配额超限
- 新设计（执行节点）：执行期间 AFS 上 0 字节，仅约 500MB 最终输出
```

### 验证执行节点使用

**检查作业是否使用执行节点存储：**

```bash
# 方法 1：检查作业输出日志
grep "Work directory for this job" Y2023_R011705_F400-450/iter01/1reco/logs/reco_*.out
# 应显示如下路径：/tmp/condor-XYZ 或 $_CONDOR_SCRATCH_DIR

# 方法 2：作业运行时，检查作业工作目录
condor_q -long <job_id> | grep "^Iwd"
# 应显示执行节点路径，而不是 AFS 路径

# 方法 3：检查 HTCondor 作业沙箱
condor_ssh_to_job <job_id> pwd
# 应显示执行节点本地路径
```

**如果作业未使用执行节点存储：**
- 检查提交文件中的 `should_transfer_files` 设置
- 验证 `initial_dir` 未设置为 AFS 路径
- 检查环境脚本中的硬编码 AFS 路径

### 存储流程图

```
[EOS 上的原始数据] 
       ↓
[HTCondor 作业启动]
       ↓
[执行节点本地磁盘]
  - 数据库副本（约 100MB）
  - 中间文件
  - 临时 ROOT 文件
       ↓
[重建过程]
       ↓
[生成输出文件]
       ↓
[传输到 EOS/AFS]
  - kfalignment_*.root
  - xAOD_*.root  
  - 日志文件
       ↓
[执行节点清理]
  - 所有临时文件被删除
  - 本地存储被释放
```

## 配置

### 基本设置

编辑 `config.json` 配置存储路径：

```json
{
  "paths": {
    "calypso_install": "/afs/cern.ch/user/y/yourusername/calypso/install",
    "pede_install": "/afs/cern.ch/user/y/yourusername/pede",
    "env_script": "reco_condor_env.sh",
    "work_dir": "/afs/cern.ch/user/y/yourusername/alignment-work",
    "eos_output_dir": "/eos/user/y/yourusername/faser-alignment-output"
  },
  "storage": {
    "use_eos_for_output": true,
    "keep_intermediate_root_files": true,
    "keep_alignment_constants": true,
    "cleanup_reco_temp_files": true
  }
}
```

### 存储选项说明

**`use_eos_for_output`** (布尔值，默认: true)
- 为 `true` 时：大输出文件（root 文件、xAOD 文件）写入 EOS
- 为 `false` 时：所有输出写入 work_dir（仅在 AFS 空间充足时使用）

**`keep_intermediate_root_files`** (布尔值，默认: true)
- 为 `true` 时：保留所有迭代的 Root 文件
- 为 `false` 时：仅保留最终迭代的 root 文件（节省空间）

**`keep_alignment_constants`** (布尔值，默认: true)
- 始终建议保留这些文件（小文件，对分析至关重要）
- 包含每次迭代的对齐参数

**`cleanup_reco_temp_files`** (布尔值，默认: true)
- 为 `true` 时：迭代完成后删除临时重建文件
- 为 `false` 时：保留所有临时文件（用于调试）

## 目录结构

### 使用 EOS 存储（推荐）

```
AFS: /afs/cern.ch/user/y/yourusername/alignment-work/
├── Y2023_R011705_F400-450/
│   ├── alignment.dag                # DAG 定义
│   ├── alignment.dag.dagman.out     # DAGman 日志
│   ├── iter01/
│   │   ├── 1reco/
│   │   │   ├── reco.sub            # 提交文件
│   │   │   ├── inputforalign.txt   # 对齐常数（小文件）
│   │   │   └── logs/               # 作业日志
│   │   └── 3millepede/
│   │       ├── millepede.sub
│   │       └── millepede.out
│   └── iter02/
│       └── ...

EOS: /eos/user/y/yourusername/faser-alignment-output/
├── Y2023_R011705_F400-450/
│   ├── iter01/
│   │   ├── 2kfalignment/           # Root 文件（大文件）
│   │   │   ├── kfalignment_*.root
│   │   │   └── xAOD_*.root
│   │   └── 3millepede/
│   │       └── millepede-result.txt
│   └── iter02/
│       └── ...
```

## 性能考虑

### 可执行文件位置

**问题**：可执行文件（Calypso、Pede）应该放在 AFS 还是 EOS？

**建议**：
- **Calypso**：保存在 **AFS**
  - 编译时间：约 1 小时（在计算节点上不可行）
  - 大小：约 230 MB（AFS 可管理）
  - 访问：从 AFS 访问更快，所有作业都使用
  
- **Pede**：可以放在 **AFS** 或 **EOS**
  - 编译时间：约 2 分钟（对于本地编译足够快）
  - 大小：约 60 MB（AFS 足够小）
  - 建议：保存在 AFS 以获得更好性能

**性能影响**：
- 从 EOS 读取可执行文件每个作业启动增加约 1-2 秒
- 对于短作业（<5 分钟），这是显著开销（约 2-5%）
- 对于长作业（>1 小时），影响可忽略不计（<0.1%）

### 最佳实践

1. **从 AFS 提交**：
   ```bash
   cd /afs/cern.ch/user/y/yourusername/alignment-work
   python3 dag_manager.py -y 2023 -r 011705 -f 400-450 -i 10 --submit
   ```

2. **配置 EOS 用于输出**：
   - 在 config.json 中设置 `eos_output_dir`
   - 大文件自动写入 EOS
   - 在 AFS 工作目录中创建符号链接以便访问

3. **监控磁盘使用**：
   ```bash
   # 检查 AFS 配额
   fs quota ~
   
   # 检查 EOS 使用情况
   eos quota /eos/user/y/yourusername
   ```

4. **完成后清理**：
   ```bash
   # 删除临时文件（如果未自动清理）
   python3 cleanup_workflow.py Y2023_R011705_F400-450
   ```

## 文件大小估计

每次迭代的典型文件大小（50 个原始文件）：

| 文件类型 | 位置 | 每次迭代大小 | 保留？ |
|---------|------|------------|--------|
| 原始文件 | EOS（输入） | 约 5 GB | 仅输入 |
| xAOD 文件 | EOS | 约 2 GB | 可选 |
| Root 文件（kfalignment） | EOS | 约 500 MB | 是 |
| 对齐常数 | AFS | 约 50 KB | 是 |
| 作业日志 | AFS | 约 10 MB | 是 |
| 临时文件 | 临时 | 约 200 MB | 否 |

**每次迭代总计**：EOS 约 2.5 GB，AFS 约 10 MB

**10 次迭代**：EOS 约 25 GB，AFS 约 100 MB

## 故障排除

### 问题：AFS 配额超限

**症状**：作业失败，显示 "Disk quota exceeded"

**解决方案**：
1. 验证 EOS 已配置：
   ```bash
   grep eos_output_dir config.json
   ```
2. 启用清理：
   ```json
   "cleanup_reco_temp_files": true
   ```
3. 删除旧工作流：
   ```bash
   rm -rf Y2023_R011705_F400-450/
   ```

### 问题：EOS 写入失败

**症状**：作业完成但输出文件缺失

**解决方案**：
1. 检查 EOS 配额：
   ```bash
   eos quota /eos/user/y/yourusername
   ```
2. 验证 EOS 目录存在：
   ```bash
   ls -la /eos/user/y/yourusername/faser-alignment-output/
   ```
3. 检查权限：
   ```bash
   eos chmod 755 /eos/user/y/yourusername/faser-alignment-output/
   ```

### 问题：作业启动缓慢

**症状**：作业启动时间长，在"I"状态停留时间长

**可能原因**：
1. EOS 上的可执行文件（读取慢）
2. 通过 HTCondor 传输的大输入文件
3. 从 EOS 设置环境

**解决方案**：
1. 将可执行文件保存在 AFS
2. 直接使用 EOS 路径（不通过文件传输）
3. 优化环境脚本

## 从旧版设置迁移

如果从 `auto_iter.py` 或 `main.py` 迁移：

**旧结构**（所有内容在一处）：
```
/eos/experiment/faser/alignment/Y2023_R011705/
├── iter01/
│   ├── 1reco/
│   ├── 2kfalignment/
│   └── 3millepede/
```

**新结构**（AFS + EOS）：
```
AFS: 提交文件、DAG、日志
EOS: Root 文件、大输出
```

## 总结

**推荐设置**：
1. ✅ 从 AFS 提交作业（在 AFS 上使用 `work_dir`）
2. ✅ 将可执行文件（Calypso、Pede）存储在 AFS 以获得性能
3. ✅ 将大输出（root 文件）存储在 EOS
4. ✅ 将对齐常数和日志保留在 AFS
5. ✅ 启用临时文件的自动清理
6. ✅ 监控 AFS 和 EOS 配额

此设置在有效管理存储的同时提供最佳性能。
