# kb-0031 evidence summary

Source: model_forge_agent tip GPU claim 验收草稿（2026-10-15），晓安哥点名「问题+方案」备审；知识库润色落 inbox。

| item | note |
|---|---|
| tip | forge-agent ~`87d94b7` |
| job 116 | PASS |
| job 117–119 | FAIL then fixed per issues 1–5 |
| PRO5000 | GPU-busy stall → restart; check log timestamps on false-busy |
| Thor lerobot | `/work/vendor/lerobot` (deps aarch64) + overlay |
| schedulable | drain old thor-2240 (thor-003); keep tip thor-2231-gpu0 |
| LIBERO q01 | tip skips missing percentiles; use ckpt norm_stats |
| mlc-vla | Thor 1.1.0 missing nvfp4_awq_calib vs PRO5000 1.1.1; hotfix then pin (no aarch64 1.1.1 full pack yet) |
| issue #6 / job 120 | claim=`thor-2231-gpu0`; validate+calib PASS; 6 calib artifacts `mfs://` by-uri 200; compile FAIL `AttributeError` `RegisterOpAttr`（栈 `tvm-relax-1.1.0-main-9d2dbedcd` + `mlc-vla-1.1.0-main-8f05e9fb9`）。Thor 钉 1.1.0 runtime（无 `libtvm_compiler.so`），PRO5000 为 1.1.1-compile + mlc 1.1.1。blocker：aarch64 `tvm-relax-1.1.1-compile` 404（`mlc-vla-1.1.1` 已有；1.1.0-compile 不算成套，未上线顶替） |
| commits | `8ddcfc7` agent（请求 `-compile` 时 runtime 不得顶替）+ QA_ISSUES #6；`890539d` Service 仅注释目标；`59341e7` 钉包 fail-fast；`cd57806` QA 清单。下一步：发布 aarch64 `tvm-relax-1.1.1-main-9f55f443f-compile` 后一次换钉 `FORGE_STACK` + `pi05-runtime.yaml` `by_arch.aarch64` + claim `stack_lock` |

对外入口只 `/kb/aiinfra/`（晋升后由 Blog 部署）；本文件仅 inbox evidence。
