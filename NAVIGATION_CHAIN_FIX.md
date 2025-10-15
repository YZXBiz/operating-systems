# Navigation Chain Fixes - Quick Reference

## Virtualization Section

| # | File | Current Previous | Should Be | Current Next | Should Be |
|---|------|------------------|-----------|--------------|-----------|
| 1 | chapter1-processes.md | `../intro.md` ❌ | DELETE | chapter2-process-api.md ✅ | ✅ |
| 2 | chapter2-process-api.md | chapter1-processes.md ✅ | ✅ | `chapter3-scheduling.md` ❌ | `chapter3-limited-direct-execution.md` |
| 3 | chapter3-limited-direct-execution.md | chapter2-process-api.md ✅ | ✅ | `chapter4-scheduling-policies.md` ❌ | `chapter4-scheduling.md` |
| 4 | chapter4-scheduling.md | chapter3-limited-direct-execution.md ✅ | ✅ | `chapter5-mlfq.md` ❌ | `chapter5-mlfq-scheduling.md` |
| 5 | chapter5-mlfq-scheduling.md | `chapter4-scheduling-policies.md` ❌ | `chapter4-scheduling.md` | `chapter6-proportional-share.md` ✅ | ✅ |
| 6 | chapter6-proportional-share.md | `chapter5-mlfq.md` ❌ | `chapter5-mlfq-scheduling.md` | `chapter7-multiprocessor.md` ❌ | `chapter7-multiprocessor-scheduling.md` |
| 7 | chapter7-multiprocessor-scheduling.md | `chapter6-limited-direct-execution.md` ❌ | `chapter6-proportional-share.md` | `chapter8-mlfq.md` ❌ | `chapter8-address-spaces.md` |
| 8 | chapter8-address-spaces.md | `chapter7-scheduling.md` ❌ | `chapter7-multiprocessor-scheduling.md` | `chapter9-free-space.md` ❌ | `chapter9-memory-api.md` |
| 9 | chapter9-memory-api.md | `chapter8-scheduling.md` ❌ | `chapter8-address-spaces.md` | chapter10-address-translation.md ✅ | ✅ |
| 10 | chapter10-address-translation.md | `chapter9-proportional-share-scheduling.md` ❌ | `chapter9-memory-api.md` | chapter11-segmentation.md ✅ | ✅ |
| 11 | chapter11-segmentation.md | `chapter10-multiprocessor-scheduling.md` ❌ | `chapter10-address-translation.md` | `chapter12-paging.md` ❌ | `chapter12-free-space-management.md` |
| 12 | chapter12-free-space-management.md | `chapter11.md` ❌ | `chapter11-segmentation.md` | chapter13-paging-introduction.md ✅ | ✅ |
| 13 | chapter13-paging-introduction.md | `chapter12-segmentation.md` ❌ | `chapter12-free-space-management.md` | `chapter14-tlb.md` ❌ | `chapter14-tlbs.md` |
| 14 | chapter14-tlbs.md | chapter13-paging-introduction.md ✅ | ✅ | chapter15-smaller-page-tables.md ✅ | ✅ |
| 15 | chapter15-smaller-page-tables.md | `chapter14-address-translation.md` ❌ | `chapter14-tlbs.md` | chapter16-swapping-mechanisms.md ✅ | ✅ |
| 16 | chapter16-swapping-mechanisms.md | chapter15-smaller-page-tables.md ✅ | ✅ | chapter17-page-replacement.md ✅ | ✅ |
| 17 | chapter17-page-replacement.md | `chapter16-segmentation.md` ❌ | `chapter16-swapping-mechanisms.md` | `chapter18-complete-vm-systems.md` ❌ | DELETE |

**Summary:** 17 chapters, 23 broken links (11 Previous, 12 Next)

---

## Concurrency Section

| # | File | Previous | Next |
|---|------|----------|------|
| 1 | chapter1-concurrency-introduction.md | - | chapter2-thread-api.md ✅ |
| 2 | chapter2-thread-api.md | chapter1-concurrency-introduction.md ✅ | chapter3-locks.md ✅ |
| 3 | chapter3-locks.md | chapter2-thread-api.md ✅ | chapter4-concurrent-data-structures.md ✅ |
| 4 | chapter4-concurrent-data-structures.md | chapter3-locks.md ✅ | chapter5-condition-variables.md ✅ |
| 5 | chapter5-condition-variables.md | chapter4-concurrent-data-structures.md ✅ | chapter6-semaphores.md ✅ |
| 6 | chapter6-semaphores.md | chapter5-condition-variables.md ✅ | chapter7-common-problems.md ✅ |
| 7 | chapter7-common-problems.md | chapter6-semaphores.md ✅ | chapter8-event-based.md ✅ |
| 8 | chapter8-event-based.md | chapter7-common-problems.md ✅ | - |

**Summary:** 8 chapters, ✅ ALL NAVIGATION LINKS CORRECT!

---

## Persistence Section

| # | File | Current Previous | Should Be | Current Next | Should Be |
|---|------|------------------|-----------|--------------|-----------|
| 1 | chapter1-io-devices.md | - | - | chapter2-hard-disk-drives.md ✅ | ✅ |
| 2 | chapter2-hard-disk-drives.md | chapter1-io-devices.md ✅ | ✅ | chapter3-raid.md ✅ | ✅ |
| 3 | chapter3-raid.md | chapter2-hard-disk-drives.md ✅ | ✅ | chapter4-files-directories.md ✅ | ✅ |
| 4 | chapter4-files-directories.md | chapter3-raid.md ✅ | ✅ | chapter5-file-system-implementation.md ✅ | ✅ |
| 5 | chapter5-file-system-implementation.md | `chapter4.md` ❌ | `chapter4-files-directories.md` | `chapter6.md` ❌ | `chapter6-locality-fast-file-system.md` |
| 6 | chapter6-locality-fast-file-system.md | chapter5-file-system-implementation.md ✅ | ✅ | chapter7-crash-consistency.md ✅ | ✅ |
| 7 | chapter7-crash-consistency.md | chapter6-locality-fast-file-system.md ✅ | ✅ | chapter8-journaling.md ✅ | ✅ |
| 8 | chapter8-journaling.md | `chapter7-flash.md` ❌ | `chapter7-crash-consistency.md` | `chapter9-lfs.md` ❌ | `chapter9-log-structured-file-system.md` |
| 9 | chapter9-log-structured-file-system.md | chapter8-journaling.md ✅ | ✅ | chapter10-flash-based-ssds.md ✅ | ✅ |
| 10 | chapter10-flash-based-ssds.md | `chapter09-log-structured-file-systems.md` ❌ | `chapter9-log-structured-file-system.md` | `chapter11-data-integrity-protection.md` ❌ | `chapter11-data-integrity.md` |
| 11 | chapter11-data-integrity.md | `chapter10-tbd.md` ❌ | `chapter10-flash-based-ssds.md` | `chapter12-tbd.md` ❌ | `chapter12-distributed-systems.md` |
| 12 | chapter12-distributed-systems.md | chapter11-data-integrity.md ✅ | ✅ | chapter13-summary.md ✅ | ✅ |
| 13 | chapter13-summary.md | chapter12-distributed-systems.md ✅ | ✅ | - | - |

**Summary:** 13 chapters, 8 broken links (4 Previous, 4 Next)

---

## Overall Summary

| Section | Total Chapters | Broken Previous | Broken Next | Total Broken |
|---------|----------------|-----------------|-------------|--------------|
| Virtualization | 17 | 11 | 12 | 23 |
| Concurrency | 8 | 0 | 0 | 0 ✅ |
| Persistence | 13 | 4 | 4 | 8 |
| **TOTAL** | **38** | **15** | **16** | **31** |

---

## Fix Template

For each broken link, use this search/replace pattern:

### Example 1: chapter2-process-api.md

**Find:**
```markdown
**Next:** [Chapter 3: Limited Direct Execution →](chapter3-scheduling.md)
```

**Replace with:**
```markdown
**Next:** [Chapter 3: Limited Direct Execution →](chapter3-limited-direct-execution.md)
```

### Example 2: chapter5-file-system-implementation.md

**Find:**
```markdown
**Previous:** [Chapter 4: Files and Directories ←](chapter4.md)
```

**Replace with:**
```markdown
**Previous:** [Chapter 4: Files and Directories ←](chapter4-files-directories.md)
```

---

## Verification Command

After fixing, verify the chain:

```bash
python3 verify_links.py 2>&1 | grep "Navigation links checked"
```

Expected output after fix: `Navigation links checked: 64` with 0 errors.
