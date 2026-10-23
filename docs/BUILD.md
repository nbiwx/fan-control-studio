# 构建说明

本文说明如何从公开源码构建飞牛 fnOS 安装包。仓库不含预编译 FPK、针对某台 NAS 的内核模块、用户数据或本机验收截图。

## 环境要求

- Python 3，用于运行构建脚本。
- 支持的构建主机：macOS Apple Silicon、macOS Intel 或 Linux x86_64。
- 构建脚本按 `packaging/fnpack-lock.json` 下载飞牛官方 `fnpack` 1.2.3，并校验 SHA-256。构建期需要访问官方文件地址；打包后的应用运行时不需要联网。
- 目标安装包为 x86 平台，飞牛应用中心需提供 `python312` 运行时。

## 构建

在仓库根目录运行：

```sh
python3 scripts/build_fpk.py --output-dir dist
```

产物包括：

```text
dist/1-fan-control-studio-1.3.9-x86.fpk
dist/1-fan-control-studio-1.3.9-x86.fpk.sha256
dist/build-report.json
```

脚本检查必需资源和清单版本、JSON 与 shell 语法、图标尺寸、桌面入口与端口配置，然后调用已校验的官方工具构建并检查归档。它只在本机生成文件，不会连接 NAS、安装应用或访问风扇接口。

### 代理与离线工具

macOS 上如果尚未缓存官方构建工具，脚本默认尝试本机代理 `http://127.0.0.1:7890`。可设置 `FANSTUDIO_BUILD_PROXY` 使用其它 HTTP/HTTPS 代理：

```sh
FANSTUDIO_BUILD_PROXY=http://127.0.0.1:7890 python3 scripts/build_fpk.py --output-dir dist
```

Linux 下可通过该变量指定构建代理；若未指定，脚本使用 Python 标准代理环境。已有的 `packaging/tools/` 文件会先按锁文件校验，不匹配时构建会停止。

## 驱动边界

公开源码不包含主板专用的二进制驱动或自动加载策略。若内核没有暴露可控的 `hwmon` PWM，先为自己的主板、内核版本和架构确认兼容驱动，再按驱动上游文档构建和审查。切勿加载为不同内核或主板构建的 `.ko`。驱动未就绪时，应用仍可读取现有温度与转速接口，但可能无法调节风扇。

## 安装

在飞牛应用中心安装 Python 3.12，再选择生成的 `.fpk` 手动安装。安装向导要求设置访问密码。应用以 root 身份运行以访问 hwmon；Web 服务要求密码登录，请限制在可信局域网，避免直接暴露到公网。默认服务端口为 18791；安装或启动前由飞牛检查端口占用。升级包时，先保留现有应用配置和必要备份。

离线归档检查不等同于在目标 NAS 上验证安装、驱动兼容或实体风扇响应。
