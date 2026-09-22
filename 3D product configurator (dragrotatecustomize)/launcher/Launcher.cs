// ============================================================
// ORBIT 3D Product Configurator - native launcher (C# / .NET 4.x)
//
// Single-file exe that:
//   1. carries the payload (node.exe + app) appended after its own
//      bytes, stamped with a fixed 32-byte marker at the end:
//        "ORBIT1:" + size(10) + "|" + crc(10) + padding
//   2. self-extracts to %LOCALAPPDATA%\Orbit3D\app on first run
//   3. starts node\node.exe src\launch.js (heartbeat lifecycle)
//   4. exits when the app window closes -> server shuts down
//
// Modes:
//   3D-Product-Configurator.exe            normal run
//   3D-Product-Configurator.exe --selftest headless payload check
//   env ORBIT_DONT_OPEN=1                  do not open browser
// ============================================================
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace OrbitLauncher
{
    class Program
    {
        const string MARKER_MAGIC = "ORBIT1:";
        const int    MARKER_LEN   = 32;
        const string AppDirName   = "Orbit3D";
        const string WindowTitle  = "ORBIT \u2014 3D Product Configurator";

        static int Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--selftest") return SelfTest();
            try { Run(); return 0; }
            catch (Exception ex)
            {
                Console.Error.WriteLine("[ORBIT] error: " + ex.Message);
                Console.WriteLine();
                Console.Write("Press Enter to close...");
                Console.ReadLine();
                return 1;
            }
        }

        static void Run()
        {
            string exePath   = Assembly.GetExecutingAssembly().Location;
            string payloadDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                AppDirName, "app");

            Console.WriteLine("  --------------------------------------------------");
            Console.WriteLine("   ORBIT - 3D Product Configurator");
            Console.WriteLine("  --------------------------------------------------");

            // ---- 1. self-extract when missing or stale ----
            string stamp = ReadStamp(exePath);
            string stampFile = Path.Combine(payloadDir, "payload.stamp");
            bool fresh = File.Exists(Path.Combine(payloadDir, "src", "launch.js"))
                      && File.Exists(stampFile)
                      && File.ReadAllText(stampFile).Trim() == stamp;
            if (!fresh)
            {
                Console.WriteLine("  First run - unpacking app...");
                ExtractPayload(exePath, payloadDir);
                Directory.CreateDirectory(payloadDir);
                File.WriteAllText(stampFile, stamp ?? "");
                Console.WriteLine("  Unpacked OK.");
            }

            // ---- 2. start the app server ----
            string hb = Path.Combine(Path.GetTempPath(),
                "orbit-hb-" + Guid.NewGuid().ToString("N").Substring(0, 8));
            File.WriteAllText(hb, "hb");

            string nodeExe  = Path.Combine(payloadDir, "node", "node.exe");
            string launchJs = Path.Combine(payloadDir, "src", "launch.js");

            var psi = new ProcessStartInfo();
            psi.FileName = nodeExe;
            psi.Arguments = "\"" + launchJs + "\"";
            psi.WorkingDirectory = payloadDir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.EnvironmentVariables["ORBIT_HEARTBEAT"] = hb;
            psi.EnvironmentVariables["ORBIT_VERSION"]   = "1.1.0";
            if (Environment.GetEnvironmentVariable("ORBIT_DONT_OPEN") == "1")
                psi.EnvironmentVariables["ORBIT_DONT_OPEN"] = "1";

            using (Process app = Process.Start(psi))
            {
                app.OutputDataReceived += delegate(object s, DataReceivedEventArgs e)
                    { if (e.Data != null) Console.WriteLine("  " + e.Data); };
                app.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e)
                    { if (e.Data != null) Console.WriteLine("  " + e.Data); };
                app.BeginOutputReadLine();
                app.BeginErrorReadLine();

                Console.WriteLine("  Starting 3D configurator window...");

                // ---- 3. wait for the app window (max 30s) ----
                IntPtr hwnd = IntPtr.Zero;
                Stopwatch sw = Stopwatch.StartNew();
                while (sw.ElapsedMilliseconds < 30000)
                {
                    hwnd = FindWindow(null, WindowTitle);
                    if (hwnd != IntPtr.Zero || app.HasExited) break;
                    Thread.Sleep(250);
                    Touch(hb);
                }

                if (hwnd != IntPtr.Zero)
                {
                    Console.WriteLine("  App window detected. Close it to quit.");
                    // wait until window closes or node dies
                    while (!app.HasExited)
                    {
                        if (FindWindow(null, WindowTitle) == IntPtr.Zero) break;
                        Thread.Sleep(400);
                        Touch(hb);
                    }
                }
                else
                {
                    // windowless / headless mode: stay alive while node lives
                    while (!app.HasExited)
                    {
                        Thread.Sleep(400);
                        Touch(hb);
                    }
                }

                if (!app.HasExited) { try { app.Kill(); } catch {} }
            }
            try { File.Delete(hb); } catch {}
        }

        // ---------------- payload plumbing ----------------
        static string ReadStamp(string exePath)
        {
            using (FileStream fs = File.OpenRead(exePath))
            {
                if (fs.Length < MARKER_LEN + 8) return null;
                fs.Seek(-MARKER_LEN, SeekOrigin.End);
                byte[] buf = new byte[MARKER_LEN];
                fs.Read(buf, 0, MARKER_LEN);
                string tail = Encoding.ASCII.GetString(buf);
                int i = tail.IndexOf(MARKER_MAGIC, StringComparison.Ordinal);
                if (i < 0) return null;
                int end = tail.IndexOf('|', i);
                if (end < 0) return null;
                // strip marker padding ('.' fill) from both fields
                return tail.Substring(i + MARKER_MAGIC.Length, end - i - MARKER_MAGIC.Length).Trim('.', ' ')
                     + "|" + tail.Substring(end + 1).Trim('.', ' ');
            }
        }

        static void ExtractPayload(string exePath, string destDir)
        {
            string stamp = ReadStamp(exePath);
            if (stamp == null) throw new Exception("no embedded payload in this exe");
            string[] parts = stamp.Split('|');
            long size = long.Parse(parts[0]);
            long expectedCrc = long.Parse(parts[1]);

            string tmpZip = Path.Combine(Path.GetTempPath(),
                "orbit-" + Guid.NewGuid().ToString("N") + ".zip");
            try
            {
                using (FileStream fs = File.OpenRead(exePath))
                {
                    fs.Seek(-MARKER_LEN - size, SeekOrigin.End);
                    using (FileStream outFs = File.Create(tmpZip))
                    {
                        byte[] buf = new byte[1 << 20];
                        long left = size;
                        long crc = 0;
                        while (left > 0)
                        {
                            int n = fs.Read(buf, 0, (int)Math.Min(left, buf.Length));
                            if (n <= 0) throw new EndOfStreamException("payload truncated");
                            outFs.Write(buf, 0, n);
                            for (int k = 0; k < n; k++) crc = (crc + buf[k]) & 0xFFFFFFFFL;
                            left -= n;
                        }
                        if (crc != expectedCrc)
                            throw new Exception("payload checksum mismatch (exe corrupted?)");
                    }
                }
                if (!Directory.Exists(destDir)) Directory.CreateDirectory(destDir);
                var pz = Process.Start("powershell.exe",
                    "-NoProfile -ExecutionPolicy Bypass -Command \"Expand-Archive -LiteralPath '" +
                    tmpZip + "' -DestinationPath '" + destDir + "' -Force\"");
                pz.WaitForExit(240000);
                if (pz.ExitCode != 0) throw new Exception("unzip failed (exit " + pz.ExitCode + ")");
                if (!File.Exists(Path.Combine(destDir, "node", "node.exe")))
                    throw new Exception("payload extracted but node.exe missing");
            }
            finally { try { File.Delete(tmpZip); } catch {} }
        }

        static void Touch(string hb)
        {
            try { File.SetLastWriteTimeUtc(hb, DateTime.UtcNow); } catch {}
        }

        // ---------------- headless self test ----------------
        static int SelfTest()
        {
            try
            {
                string exePath = Assembly.GetExecutingAssembly().Location;
                string stamp = ReadStamp(exePath);
                if (stamp == null) { Console.WriteLine("SELFTEST FAIL: no payload stamp"); return 2; }
                Console.WriteLine("SELFTEST: stamp=" + stamp);
                string tmp = Path.Combine(Path.GetTempPath(), "orbit-selftest-" + Guid.NewGuid().ToString("N").Substring(0, 6));
                ExtractPayload(exePath, tmp);
                bool ok = File.Exists(Path.Combine(tmp, "node", "node.exe"))
                       && File.Exists(Path.Combine(tmp, "src", "launch.js"))
                       && File.Exists(Path.Combine(tmp, "src", "app.html"))
                       && File.Exists(Path.Combine(tmp, "src", "assets", "three.min.js"));
                Console.WriteLine(ok ? "SELFTEST PASS" : "SELFTEST FAIL: payload incomplete");
                try { Directory.Delete(tmp, true); } catch {}
                return ok ? 0 : 3;
            }
            catch (Exception ex)
            {
                Console.WriteLine("SELFTEST FAIL: " + ex.Message);
                return 4;
            }
        }

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    }
}
