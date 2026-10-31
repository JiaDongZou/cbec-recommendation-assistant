# 公开版本复核 · 2026-10-31

- 在整理后的公开源码目录运行 `python -m cbec.pipeline --source demo`：128 个训练会话，32 个验证会话，数据来源明确标记为 synthetic demo。
- 运行 `python -m pytest -q`：3 passed。依赖发出一条 Starlette TestClient 关于 httpx 的弃用提示，不影响本次测试通过。
- 在公开前端目录运行 `npm run build`：Vite 5.4.21 生产构建通过，25 个模块转换成功。
- 复核复用了本机已有的 Python 虚拟环境和前端依赖；没有执行全新环境安装。它们没有放入公开仓库。
- 发布文件仅包含源码、配置示例、说明、测试和空的数据目录；不包含原始/生成数据、环境、缓存或密钥。
- 没有运行真实 OTTO 数据、线上实验或 Docker。合成指标不能用于真实业务效果结论。
