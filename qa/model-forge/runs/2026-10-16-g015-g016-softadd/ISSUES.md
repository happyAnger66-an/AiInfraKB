# ISSUES — SoftAdd G2（G-006…G-016 摘要）

作者：`agent:QA测试/box`  
口径：Agent 修一件 → QA **新开一单**（勿刷失败 job）。

说明：下表「症状→归属→关单证据」以测栈 job `#7`…`#20` 与群内确认号为准。  
**板号已对齐群聊的**：**G-013 / G-015 / G-016**。  
G-006…G-012、G-014 按本轮 SoftAdd 阻塞出现顺序与关单旁证回填（便于复用）；若看板旧称不一致，以症状+证据 job 为准，不改写历史 job alias。

| ID | 症状（摘要） | 归属 | 暴露 job | 关单证据 |
|---|---|---|---|---|
| G-006 | calib `ModuleNotFoundError: gr00t`（Isaac-GR00T 未进解释器路径） | model_forge_agent | `#7` `#9` | 后续 calib 能 import；旁证 `#12+` dit calib 可写 scales |
| G-007 | `GR00T calib 需要 calib.fp8_out`（adapt_recipe 未写） | model_forge_agent | `#10` `#11` | `#12+` 不再报 fp8_out |
| G-008 | LLM calib：`from_pretrained` 落在 meta device | model_forge_agent | `#12` | `#13` 改走 `from_config` + backbone assets |
| G-009 | `make_xdof_obs() unexpected keyword argument 'seed'` | model_forge_agent | `#13` | `#14` 越过该 TypeError |
| G-010 | LLM calib 缺 `mm_token_type_ids`（M-RoPE） | model_forge_agent | `#14` | `#15` calib 全绿进入 compile |
| G-011 | compile：scale 表缺 LLM 键（例 176 条 `llm.layers.*.*_scale`） | agent / 配方 scopes | `#15` | SoftAdd 路线改为 dit scales 主路径；`#17` 起灌 384/656 SoftAdd scales |
| G-012 | SoftAdd calib 依赖 `albumentations` 版本/路径漂移前兆（pydeps） | model_forge_agent | `#16` 前布置 | 与 G-013 一并收口 |
| **G-013** | SoftAdd calib：`albumentations` 无 `ImageOnlyTransform`；需 `PI05_EXTRA_PYTHONPATH`/pydeps_gr00t | model_forge_agent | `#16` `QA-G2-r8-softadd-scales` | `#17` calib PASS（alias 含 g013） |
| G-014 | SoftAdd 任务须钉 C1 `LD_PRELOAD=…/phase_a_so/libsynapsex_fp8_gemm_c1.so`，踢掉 tip `n3fc2` | 算子开发 / agent env | 任务 env 冒烟 | 算子侧 `C1_SMOKE_OK`（本轮群内确认）；glue 前看护 |
| **G-015** | dit compile `KeyError` 缺 65× `adaln_static_scale/shift_*` + `proj_out_1_static`；根因 loader 未 fold AdaStatic bank | 模型编译（mlc-vla）+ agent 热补过渡 | `#17`（热补前） | **正式包** pin `mlc-vla-2.0.1-…-ddea2af79`；撤热补；`#19` compile PASS |
| **G-016** | unirt_pack：交付缺 `stats.json`（ckpt 仅有 Isaac `statistics.json`，非 openpi normalizer） | model_forge_agent (`22863b1`) | `#18` `#19` pack FAIL | **`#20` PASS**：日志「交付补齐 stats.json ← statistics.json」；pack `/data/packs/QA-G2-r12-g016-stats` |

## 仍开 / 缺口

| ID | 症状 | 归属 | 证据 | 状态 |
|---|---|---|---|---|
| （glue） | `JobRunner` 无 `_run_gr00t_compare` | model_forge_agent | `#22` | open — 修好后 **新开** compare，勿刷 `#22` |
| （UI） | 测栈 web 旧镜像无 GR00T 入口；API≠UI | model_forge_web | 镜像 `9b764d5` | open — 升 `:18088` 后 QA 补 UI 冒烟 |

## G-015 两层（勿混关）

1. **热补层**：测容器 `fold_static_adaln_bank` / patches 卷 → 仅证明可编。  
2. **正式包层**：service pin `2.0.1@ddea2af` + 撤热补 → `#19` compile 才算 G-015 结案。
