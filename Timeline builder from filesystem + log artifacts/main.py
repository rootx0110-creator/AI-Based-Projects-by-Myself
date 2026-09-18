import argparse
import os
import sys


def cli(args):
    from timeline_core import Scanner, build_stats
    from timeline_report import build_html_report

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print("ERROR: folder does not exist: {}".format(root))
        return 2
    print("Scanning {}...".format(root))
    scanner = Scanner(include_accessed=not args.no_accessed,
                      parse_logs=not args.no_logs)
    events, stats = scanner.scan(root, progress=lambda m: print("  " + m))
    stats = build_stats(events, stats)
    print("\n=== Scan summary ===")
    print("Files         : {}".format(stats["files"]))
    print("Folders       : {}".format(stats["dirs"]))
    print("Log files     : {}".format(stats["log_files"]))
    print("Log lines     : {}".format(stats["log_lines"]))
    print("Events total  : {}".format(len(events)))
    print("Events by type: {}".format(
        ", ".join("{}={}".format(k, v) for k, v in stats["counts"].items())))
    print("Earliest      : {}".format(stats["first"]))
    print("Latest        : {}".format(stats["last"]))
    print("Time span     : {} days".format(stats["span_days"]))
    if args.out:
        html = build_html_report(events, stats,
                                 options={"title": args.title})
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("\nHTML report  -> {}".format(os.path.abspath(args.out)))
    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "type", "source", "path", "details",
                        "size_bytes"])
            for e in events:
                w.writerow([e.ts.strftime("%Y-%m-%d %H:%M:%S"), e.type,
                            e.source, e.path, e.details,
                            e.size if e.size is not None else ""])
        print("CSV export   -> {}".format(os.path.abspath(args.csv)))
    return 0


def main():
    if "--cli" in sys.argv:
        parser = argparse.ArgumentParser(
            prog="TimelineBuilder",
            description="Build a timeline from filesystem metadata and log "
                        "artifacts.")
        parser.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)
        parser.add_argument("path", help="root folder to scan")
        parser.add_argument("--out", help="write HTML report to this file")
        parser.add_argument("--csv", help="write CSV export to this file")
        parser.add_argument("--title", default="Timeline Report",
                            help="report title")
        parser.add_argument("--no-accessed", action="store_true",
                            help="skip last-accessed events")
        parser.add_argument("--no-logs", action="store_true",
                            help="skip log artifact parsing")
        args = parser.parse_args()
        sys.exit(cli(args))

    try:
        from timeline_app import run
        run()
    except Exception as exc:
        import traceback
        import os
        tb = traceback.format_exc()
        tb_log = os.environ.get("TBLOG", "")
        if tb_log:
            with open(tb_log, "a", encoding="utf-8") as fh:
                fh.write(tb + "\n")
        else:
            traceback.print_exc()
            input("Fatal error (see above). Press Enter to exit...")


if __name__ == "__main__":
    main()