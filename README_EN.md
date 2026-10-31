# C3RB3R / .L0CK3D: a Synology DSM recovery journal

[简体中文](README.md) | English

A personal incident report covering live-process preservation, partial process-memory capture, session-material validation, photo recovery, Live Photo pairing and resumable batch verification. The machine was an i3-8100T bare-metal DSM system presenting as DS918+, not a PVE guest. **The rescue workstation can run Windows, macOS or Linux. Mac was the workstation used in this historical case, not a requirement of the recovery method.**

## Platform scope

NAS-side process preservation, ciphertext analysis and verification principles are independent of the workstation OS. The bundled Python audit helper has been adapted for Windows, macOS and Linux; this revision was tested locally on macOS only. CI is configured for all three platforms but remote results are not yet available.

Network commands, paths, permissions and media APIs differ. Historical macOS `route`/`tcpdump`, `.command` launchers and Apple `PHLivePhoto` checks are not Windows commands. See the [cross-platform guide](docs/11-cross-platform.md) for PowerShell examples and limits. On Windows use `py -3` instead of `python3` and protect outputs using NTFS ACLs; a POSIX mode of 0600 does not establish Windows privacy.

## Results at the evidence cutoff

**2026-10-31 16:08, UTC+08:00.** This is a historical evidence cutoff, not live monitoring.

| Scope | Recorded result | Limit |
|---|---|---|
| Memory | Two v2 captures, 19 mappings | Both have 12,288 unreadable bytes; not full RAM |
| Encrypted photo-tree files | 63,667 recovered outputs, 98,064,905,843 bytes | Includes thumbnails and metadata; 9,423 are main photos/videos |
| Historical originals | Four exact SHA-256 matches | Does not establish correctness of all other files |
| Live Photos | 3,727 pairs, 7,454 additional copies | Derived copies are not new originals; 76 unpaired items remain |
| Shared directory | 1,288 decrypted + 53 copied | No exact historical originals; application acceptance pending |
| Six small directories | 225 decrypted + 96 copied | Twelve naming conflicts preserved; one JSON syntax exception |
| homes | 73,094 files accepted at file level | Package 0008 accepted; 0009 in progress; whole tree unfinished |

System trust, application consistency and independent-device backups remain unfinished. Later batches wrote archives and new outputs to the affected NAS because of capacity constraints. Those are rollback copies on the same failure domain, not independent backups or a recommended default architecture.

## What this case contributes

- Mac TCP failed locally with `Cannot allocate memory`; packet capture and removal of a temporary static host route resolved it.
- Captures with identical holes remained explicitly marked partial. Transport hashes did not turn unreadable pages into evidence.
- The initial footer rejection preceded key validation. The incident marker `e921db3b` was configured explicitly while preserving all other checks, followed by exact-original comparison.
- Recursive copying hid case collisions and permission gaps. Path manifests and individual hashes established coverage.
- Internal asset identifiers corrected five misleading same-name Live Photo pairs.
- A broken connection left 1,817 NAS receipts versus 1,816 Mac acknowledgements. Reconciliation preceded package-based continuation.

## Reading and tools

The detailed case chapters are in Chinese. Start with the [runbook](docs/00-runbook.md), [results and limits](docs/07-results-and-limits.md), [source review](docs/10-source-review.md) and [tool reference](tools/README.md).

`tools/rescue_audit.py` is a new Python 3.9+ standard-library helper for offline manifests, exact-path hash comparison, EOF layout inspection and collision-aware output planning. It does not acquire memory, extract keys, decrypt files, access block devices or connect to a NAS.

```sh
python3 tools/rescue_audit.py --help
python3 -m unittest discover -s tests -v
```

Preserve evidence before rebooting, upgrading, reinstalling or terminating an identified encryptor. Choose independent storage, validate copies first and distinguish output integrity, historical-original equality, decoding and application acceptance. Never reuse this case's PID, interface or marker without checking your own evidence.

## References and license

Inspired by [soimy/c3rb3r-rescue](https://github.com/soimy/c3rb3r-rescue), [sunkangbo121-ship-it/c3rb3r-btrfs-extent-rescue](https://github.com/sunkangbo121-ship-it/c3rb3r-btrfs-extent-rescue), and [crt106/c3rb3r-btrfs-recovery](https://github.com/crt106/c3rb3r-btrfs-recovery). This incident used its own memory-derived session material. Btrfs recovery is a referenced alternative, not a tested result from this incident.

No third-party recovery code, memory images, keys, ciphertext, personal media, credentials or raw private chats are distributed. Original content is [MIT licensed](LICENSE). See [security and privacy](SECURITY.md) before sharing diagnostics.
