# Quick Reference

## 1. Find MBIDs

```bash
# Search for a song
uv run --package module2 python -m module2.lookup --search "Foo Fighters Congregation"

# Check if it has LB neighbor data
uv run --package module2 python -m module2.lookup --check 1eac49da-3399-4d34-bbf3-a98a91e2758b
```

## 2. Generate Playlist — Module 2 (beam search only)

```bash
uv run --package module2 python -m module2.main \
  --source 1eac49da-3399-4d34-bbf3-a98a91e2758b \
  --dest 80c24793-6a40-4edb-b1bb-5a4e3946901e
```

## 3. Generate Playlist — Module 3 (full pipeline)

```bash
uv run --package module3 python -m module3.main \
  --source 2c5f1ac6-d41d-455c-998d-6f572f64a797 \
  --dest 3eea5cf7-feba-49bc-be94-1b155dbcb165
```

## 4. Flags

```bash
uv run --package module3 python -m module3.main \
  --source <MBID> \
  --dest <MBID> \
  --length 5 \          # playlist size (default: 7)
  --beam-width 15 \     # search breadth (default: 10)
  --json \              # JSON output instead of pretty-print
  --no-essentia         # skip Essentia audio fallback
```

## 5. Run Tests

```bash
# All module 3 tests (80)
uv run --package module3 pytest modules/module3/src/module3/tests/ -v

# All module 2 tests (35)
uv run --package module2 pytest modules/module2/ -v

# Everything
just test
```

## Known Working MBIDs

| Track | MBID |
|-------|------|
| Foo Fighters — Congregation | `1eac49da-3399-4d34-bbf3-a98a91e2758b` |
| Royal Blood — Little Monster | `80c24793-6a40-4edb-b1bb-5a4e3946901e` |
| Florence — What Kind of Man | `ffcb45c3-7f32-427d-b3d4-287664bbcdb9` |
| Pink Floyd — Lost Art of Conversation | `564ccd5c-c4d3-4752-9abf-c33bb085d6a5` |
