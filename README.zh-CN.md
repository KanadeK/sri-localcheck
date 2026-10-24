# sri-localcheck

检查现有 HTML 中的 `integrity` 声明是否匹配本地构建产物的实际字节，提前发现过期哈希。
Python 3.11+，仅用标准库。[English](README.md)。

无需启动服务器，不执行 JavaScript，不访问 CDN，也不自动重写哈希掩盖问题。
远程 URL 无法由本地文件证明，因此明确失败。

## 安装与演示

```sh
git clone https://github.com/KanadeK/sri-localcheck.git
cd sri-localcheck
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# POSIX: . .venv/bin/activate
python -m pip install .
sri-localcheck examples/site valid.html --json
sri-localcheck examples/site broken.html --json
```

第一条退出 0；第二条退出 1：正确的 SHA-256 不能挽救错误的 SHA-512。
`remote.html` 会在不访问网络的情况下失败。示例 JS/CSS 均为原创合成数据，
可运行独立生成脚本 `python scripts/make_examples.py` 复现。
也可从 [v0.1.0 Release](https://github.com/KanadeK/sri-localcheck/releases/tag/v0.1.0)
下载 wheel 与 SHA256SUMS，核对后执行
`python -m pip install sri_localcheck-0.1.0-py3-none-any.whl`。
发布渠道为 GitHub Release，不表示已上传 PyPI。

```sh
python -m sri_localcheck dist pages/index.html --json
sri-localcheck dist pages/index.html --require-integrity --json
```

HTML 路径相对于构建根目录。默认只检查 `script[src]` 和
`link[rel~=stylesheet]` 上已有的声明；`--require-integrity` 还会报告这些元素缺少声明。
其他带有 integrity 的元素，包括 preload/modulepreload 与内联 script，报告不支持。

退出码 **0**：至少检查一条声明且全部通过；**1**：声明、资源、路径、歧义或远程未验证问题；
**2**：根目录/HTML/编码/数量限制错误，或没有可检查声明。空页面或零声明不会默认通过。

## 验证规则

- 支持 SHA-256/384/512，仅使用存在的最强算法；同强度的多个候选有一个匹配即可。
  算法名和元数据语法区分大小写。
- 支持标准或 URL-safe Base64、规范填充或无填充；拒绝错误长度、非零填充位、
  多余填充、未知/损坏算法和 `?option`。这比浏览器可能忽略无效 token 的行为更严格，
  不宣称完整模拟浏览器 SRI。
- 支持相对/根相对 URL 和一个本地 `<base href>`；HTML 实体与 UTF-8 `%HH`
  解码一次。查本地文件时忽略 query/fragment，假设 query 不选择不同表示。
  不按浏览器的解析、请求和脚本执行时序运行。
- 任何显式协议或 `//` URL 都未验证，包括自己网站的绝对 URL；外部、空、重复或歧义
  base 会失败。元数据和资源路径不会被自动修正。
- 资源必须位于真实构建根目录内。拒绝符号链接、Windows reparse、编码后的 `..`、
  反斜杠、设备/ADS 名称、错误百分号编码、重复斜杠和尾点/空格。为跨平台一致，
  Windows 保留文件名在所有系统上都拒绝。普通 `../assets/app.js` 经 URL 解析后
  仍在根目录内时可以使用。

限制：HTML 为 UTF-8（可有 BOM），不超过 2 MiB；最多 1,000 个候选元素，包含没有声明
的受支持资源；每条最多 64 个哈希 token；每个资源 16 MiB，总读取 64 MiB。
失败读取也计入总预算，溢出探测最多额外读 1 字节。完整成功读取的资源哈希按相对路径缓存，
每个元素仍使用各自的预期哈希。

使用稳定、停止写入的构建目录。读取前后核对文件状态，但没有原子快照，也不保证对抗并发
恶意写入；缓存复用期间文件也应保持不变。本地字节验证不代表 HTTP 编码、服务器改写、
CORS/CSP、MIME、动态 DOM、部署或浏览器执行正确；HTML 与资源一起被替换时也不能证明来源。

## 报告与维护

JSON `sri-localcheck/v1` 含 HTML SHA-256、计数、读取字节、缓存数和元素行号/类型/
问题码/算法/大小。不输出正文、预期摘要、URL、query 值或磁盘路径。HTML 哈希仍是稳定
指纹，脱敏并非匿名化；argparse 用法错误沿用常规命令行行为。

需求实例：[Magento 的 SRI 不匹配问题](https://github.com/magento/magento2/issues/40807)，
该问题已在上游修复后关闭。算法选择参考
[W3C SRI Recommendation](https://www.w3.org/TR/2016/REC-SRI-20160623/)。
[jkittner/sri-checker](https://github.com/jkittner/sri-checker) 为相邻 HTML linter，
其 CDN 流程需要网络。本项目专注离线核对已有声明，与本账号 assetwire 的部署响应验证、
sidecar-verify 的压缩旁路文件验证和 AssetMatrix 的图片变体/尺寸检查范围不同。

```sh
python -m pip install -e ".[dev]"
python scripts/verify.py
```

门禁包含 Ruff、分支覆盖率至少 90%、回归测试、源码包/wheel 构建与仓库外干净安装演示。
CI 为 Ubuntu Python 3.11/3.13、Windows/macOS 3.13，仅读权限，并核对完整提交历史中的
维护者 Author/Committer 身份。无运行时依赖或第三方实现打包。
参见 [验证说明](VALIDATION.md)、[来源](THIRD_PARTY.md)、
[贡献政策](CONTRIBUTING.md)、[安全报告](SECURITY.md)。

卸载：`python -m pip uninstall sri-localcheck`，按需删除虚拟环境与克隆目录。
检查器不生成配置、磁盘缓存或远程状态。MIT 协议；新增 URL/HTML 覆盖应有真实问题和回归
样例依据，避免静默猜测行为。
