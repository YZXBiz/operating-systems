# Files Requiring Link Fixes

Quick reference for which files need updates.

## Critical: Broken Navigation Links (Must Fix)

### Virtualization (21 files)

1. ✅ `docs/virtualization/chapter1-processes.md`
   - Previous: `../intro.md` → DELETE (no intro exists)

2. ✅ `docs/virtualization/chapter2-process-api.md`
   - Next: `chapter3-scheduling.md` → `chapter3-limited-direct-execution.md`

3. ✅ `docs/virtualization/chapter3-limited-direct-execution.md`
   - Next: `chapter4-scheduling-policies.md` → `chapter4-scheduling.md`

4. ✅ `docs/virtualization/chapter4-scheduling.md`
   - Next: `chapter5-mlfq.md` → `chapter5-mlfq-scheduling.md`

5. ✅ `docs/virtualization/chapter5-mlfq-scheduling.md`
   - Previous: `chapter4-scheduling-policies.md` → `chapter4-scheduling.md`

6. ✅ `docs/virtualization/chapter6-proportional-share.md`
   - Previous: `chapter5-mlfq.md` → `chapter5-mlfq-scheduling.md`
   - Next: `chapter7-multiprocessor.md` → `chapter7-multiprocessor-scheduling.md`

7. ✅ `docs/virtualization/chapter7-multiprocessor-scheduling.md`
   - Previous: `chapter6-limited-direct-execution.md` → `chapter6-proportional-share.md`
   - Next: `chapter8-mlfq.md` → `chapter8-address-spaces.md`

8. ✅ `docs/virtualization/chapter8-address-spaces.md`
   - Previous: `chapter7-scheduling.md` → `chapter7-multiprocessor-scheduling.md`
   - Next: `chapter9-free-space.md` → `chapter9-memory-api.md`

9. ✅ `docs/virtualization/chapter9-memory-api.md`
   - Previous: `chapter8-scheduling.md` → `chapter8-address-spaces.md`

10. ✅ `docs/virtualization/chapter10-address-translation.md`
    - Previous: `chapter9-proportional-share-scheduling.md` → `chapter9-memory-api.md`

11. ✅ `docs/virtualization/chapter11-segmentation.md`
    - Previous: `chapter10-multiprocessor-scheduling.md` → `chapter10-address-translation.md`
    - Next: `chapter12-paging.md` → `chapter12-free-space-management.md`

12. ✅ `docs/virtualization/chapter12-free-space-management.md`
    - Previous: `chapter11.md` → `chapter11-segmentation.md`

13. ✅ `docs/virtualization/chapter13-paging-introduction.md`
    - Previous: `chapter12-segmentation.md` → `chapter12-free-space-management.md`
    - Next: `chapter14-tlb.md` → `chapter14-tlbs.md`

14. ✅ `docs/virtualization/chapter15-smaller-page-tables.md`
    - Previous: `chapter14-address-translation.md` → `chapter14-tlbs.md`

15. ✅ `docs/virtualization/chapter17-page-replacement.md`
    - Previous: `chapter16-segmentation.md` → `chapter16-swapping-mechanisms.md`
    - Next: `chapter18-complete-vm-systems.md` → DELETE (doesn't exist yet)

### Persistence (8 files)

16. ✅ `docs/persistence/chapter5-file-system-implementation.md`
    - Previous: `chapter4.md` → `chapter4-files-directories.md`
    - Next: `chapter6.md` → `chapter6-locality-fast-file-system.md`

17. ✅ `docs/persistence/chapter8-journaling.md`
    - Previous: `chapter7-flash.md` → `chapter7-crash-consistency.md`
    - Next: `chapter9-lfs.md` → `chapter9-log-structured-file-system.md`

18. ✅ `docs/persistence/chapter10-flash-based-ssds.md`
    - Previous: `chapter09-log-structured-file-systems.md` → `chapter9-log-structured-file-system.md`
    - Next: `chapter11-data-integrity-protection.md` → `chapter11-data-integrity.md`

19. ✅ `docs/persistence/chapter11-data-integrity.md`
    - Previous: `chapter10-tbd.md` → `chapter10-flash-based-ssds.md`
    - Next: `chapter12-tbd.md` → `chapter12-distributed-systems.md`

---

## Medium Priority: TOC Anchor Format Issues

### Files with Triple-Dash Issues (3 files)

20. ✅ `docs/concurrency/chapter2-thread-api.md`
    - TOC line 26: Change `#24-creating-a-thread---complete-example` → `#24-creating-a-thread-complete-example`

21. ✅ `docs/persistence/chapter4-files-directories.md`
    - TOC line: Change `#2-files-and-directories---core-abstractions` → `#2-files-and-directories-core-abstractions`

22. ✅ `docs/virtualization/chapter16-swapping-mechanisms.md`
    - Multiple TOC entries need `---` changed to `-`:
      - `#1-introduction---the-memory-illusion` → `#1-introduction-the-memory-illusion`
      - `#2-swap-space---your-memory-safety-net` → `#2-swap-space-your-memory-safety-net`
      - `#23-beyond-swap---code-pages` → `#23-beyond-swap-code-pages`
      - `#3-the-present-bit---memorys-truth-detector` → `#3-the-present-bit-memorys-truth-detector`
      - `#4-the-page-fault-handler---crisis-management` → `#4-the-page-fault-handler-crisis-management`
      - `#5-when-memory-is-full---the-replacement-problem` → `#5-when-memory-is-full-the-replacement-problem`
      - `#6-page-fault-control-flow---the-complete-picture` → `#6-page-fault-control-flow-the-complete-picture`
      - `#7-when-replacements-really-occur---proactive-memory-management` → `#7-when-replacements-really-occur-proactive-memory-management`

### Files with Missing Suffixes in TOC (3 files)

23. ✅ `docs/virtualization/chapter2-process-api.md`
    - TOC: `#63-the-superuser` → `#63-the-superuser-root`

24. ✅ `docs/virtualization/chapter6-proportional-share.md`
    - TOC: `#62-stride-vs-lottery-tradeoffs` → Already correct (check actual header)

25. ✅ `docs/virtualization/chapter14-tlbs.md`
    - TOC: `#62-solution-1-flush-on-switch` → `#62-solution-1-flush-on-context-switch`
    - TOC: `#63-solution-2-address-space-identifiers` → `#63-solution-2-address-space-identifiers-asids`

---

## Low Priority: README Anchor Links

### Files to Update (4 READMEs)

26. ✅ `docs/README.md`
    - Check link to `persistence/chapter2-hard-disk-drives.md#5-disk-scheduling`

27. ✅ `docs/concurrency/README.md`
    - Multiple anchor links need verification (7 links)

28. ✅ `docs/persistence/README.md`
    - Multiple anchor links need verification (13 links)

---

## Fix Checklist

- [ ] **Phase 1: Navigation Chain** (Files 1-19)
  - [ ] Fix all virtualization navigation links
  - [ ] Fix all persistence navigation links
  - [ ] Test navigation by clicking through chain

- [ ] **Phase 2: TOC Anchors** (Files 20-25)
  - [ ] Fix triple-dash issues
  - [ ] Fix missing suffix issues
  - [ ] Verify each TOC link works

- [ ] **Phase 3: README Links** (Files 26-28)
  - [ ] Investigate each broken README anchor
  - [ ] Update README or create missing sections
  - [ ] Test all README links

- [ ] **Phase 4: Verification**
  - [ ] Run `python3 verify_links.py` again
  - [ ] Confirm 0 errors
  - [ ] Address any remaining warnings

---

## Quick Stats

- **Total files requiring changes:** 28
- **Broken navigation links:** 92 (in 19 files)
- **Broken TOC anchors:** 14 (in 6 files)
- **Broken README anchors:** 22 (in 3 files)

---

## Commands

```bash
# Run verification
python3 verify_links.py

# Run and save output
python3 verify_links.py > output.txt 2>&1

# Count remaining errors
python3 verify_links.py 2>&1 | grep "❌ ERRORS"
```
