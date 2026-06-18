# examples/mini-vault — 데모 코퍼스 & eval 픽스처

이 폴더는 `llm-vault` **프레임워크 템플릿**이 어떻게 동작하는지 보여주기 위한 **최소
데모 vault**입니다. 실제 지식이 아니라 예시이며, 검색·그래프·평가(eval)의 재현 가능한
픽스처 역할을 합니다.

> public `llm-vault`는 빈 프레임워크 스켈레톤 + 이 mini-vault만 담습니다. 실제 지식
> 코퍼스는 개인 private 인스턴스(예: `llm-vault-private`)의 main vault에만 둡니다.
> 자세한 경계는 [SETUP.md](../../SETUP.md) §8 참조.

## 내용

| 경로 | 보여주는 것 |
|------|-------------|
| `20_Concepts/` | 원자 개념 노드 + 9-predicate 엣지 (Tokenizer↔BPE, Transformer→Tokenizer) |
| `30_Projects/Example Project.md` | 프로젝트가 개념을 `utilizes` 하는 그래프 연결 |
| `40_Decisions/2026-01-01-example-decision.md` | 결정 기록(decision record) 형식 |
| `50_Source_Summaries/` | source-summary가 `06_Raw` 원본을 그래프상 대리하는 방식 |
| `10_MOC/Example MOC.md` | MOC가 코퍼스를 묶는 방식 |
| `eval_queries.json` | 검색 품질 평가용 쿼리셋(ground truth) |

## 실행 (저장소 루트에서)

```bash
# 1) mini-vault를 별도 DB로 인덱싱 (인덱서는 상대 --db를 vault 루트 기준으로 풀므로
#    "fixture.db"는 examples/mini-vault/fixture.db 로 생성된다)
python3 90_Engine/indexer.py --vault examples/mini-vault --db fixture.db --force --embed

# 2) eval 실행 (기본값이 이 mini-vault 픽스처를 가리킴)
python3 90_Engine/eval_retrieval.py
```

`eval_retrieval.py`의 기본 `--db/--queries/--vault-root`가 이 픽스처
(`examples/mini-vault/fixture.db`, `eval_queries.json`)를 가리킵니다. 실제 vault를
평가하려면 `--vault-root . --queries <real>.json --db 90_Engine/ltm_cache.db`로
덮어쓰면 됩니다. (`fixture.db`는 빌드 산출물이라 `.gitignore` 처리됩니다.)
