// 极简二进制差分：生成/应用补丁。无第三方依赖，用 Windows 自带的 csc.exe 即可编译。
// 格式（GZip 压缩）：magic "TDBD1" | 原文件长度 | 原文件SHA1 | 新文件长度 | 新文件SHA1 | 操作流
//   操作 0 = COPY  varint(原文件偏移) varint(长度)
//   操作 1 = LIT   varint(长度) 字节
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;

public static class BinDelta
{
    const int BLOCK = 2048;
    static readonly byte[] MAGIC = { (byte)'T', (byte)'D', (byte)'B', (byte)'D', (byte)'1' };

    static byte[] Sha1(byte[] b) { using (var s = SHA1.Create()) return s.ComputeHash(b); }
    static string Hex(byte[] b) { var c = new char[b.Length * 2]; for (int i = 0; i < b.Length; i++) { c[i * 2] = "0123456789abcdef"[b[i] >> 4]; c[i * 2 + 1] = "0123456789abcdef"[b[i] & 15]; } return new string(c); }

    static void WriteVar(Stream s, long v) { while (v >= 0x80) { s.WriteByte((byte)(v | 0x80)); v >>= 7; } s.WriteByte((byte)v); }
    static long ReadVar(Stream s) { long v = 0; int shift = 0; while (true) { int b = s.ReadByte(); if (b < 0) throw new EndOfStreamException(); v |= (long)(b & 0x7F) << shift; if ((b & 0x80) == 0) return v; shift += 7; } }

    static long Hash(byte[] d, int off)
    {
        unchecked { long h = 1469598103934665603; for (int i = 0; i < BLOCK; i++) { h ^= d[off + i]; h *= 1099511628211; } return h; }
    }

    public static void Create(string oldPath, string newPath, string outPath)
    {
        byte[] o = File.ReadAllBytes(oldPath), n = File.ReadAllBytes(newPath);
        var index = new Dictionary<long, List<int>>();
        for (int i = 0; i + BLOCK <= o.Length; i += BLOCK)
        {
            long h = Hash(o, i);
            List<int> l;
            if (!index.TryGetValue(h, out l)) { l = new List<int>(); index[h] = l; }
            if (l.Count < 8) l.Add(i);
        }

        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionMode.Compress))
        {
            gz.Write(MAGIC, 0, MAGIC.Length);
            WriteVar(gz, o.Length); gz.Write(Sha1(o), 0, 20);
            WriteVar(gz, n.Length); gz.Write(Sha1(n), 0, 20);

            var lit = new List<byte>();
            int p = 0;
            while (p < n.Length)
            {
                int bestOff = -1, bestLen = 0;
                if (p + BLOCK <= n.Length)
                {
                    List<int> cands;
                    if (index.TryGetValue(Hash(n, p), out cands))
                    {
                        foreach (int c in cands)
                        {
                            int len = 0;
                            while (p + len < n.Length && c + len < o.Length && n[p + len] == o[c + len]) len++;
                            if (len > bestLen) { bestLen = len; bestOff = c; }
                        }
                    }
                }
                if (bestLen >= BLOCK)
                {
                    if (lit.Count > 0) { gz.WriteByte(1); WriteVar(gz, lit.Count); foreach (byte b in lit) gz.WriteByte(b); lit.Clear(); }
                    gz.WriteByte(0); WriteVar(gz, bestOff); WriteVar(gz, bestLen);
                    p += bestLen;
                }
                else { lit.Add(n[p]); p++; }
            }
            if (lit.Count > 0) { gz.WriteByte(1); WriteVar(gz, lit.Count); foreach (byte b in lit) gz.WriteByte(b); }
        }
    }

    // 返回值：0 成功，2 原文件不符，3 结果校验失败
    public static int Apply(string oldPath, string deltaPath, string outPath)
    {
        byte[] o = File.ReadAllBytes(oldPath);
        using (var fs = File.OpenRead(deltaPath))
        using (var gz = new GZipStream(fs, CompressionMode.Decompress))
        {
            var magic = new byte[5];
            ReadFull(gz, magic, 5);
            for (int i = 0; i < 5; i++) if (magic[i] != MAGIC[i]) { Console.Error.WriteLine("补丁文件格式不对"); return 3; }

            long oldLen = ReadVar(gz); var oldHash = new byte[20]; ReadFull(gz, oldHash, 20);
            long newLen = ReadVar(gz); var newHash = new byte[20]; ReadFull(gz, newHash, 20);

            if (o.Length != oldLen || Hex(Sha1(o)) != Hex(oldHash))
            {
                Console.Error.WriteLine("原文件与补丁不匹配（可能已打过补丁、版本不同，或文件被改过）");
                Console.Error.WriteLine("  需要 SHA1: " + Hex(oldHash));
                Console.Error.WriteLine("  实际 SHA1: " + Hex(Sha1(o)));
                return 2;
            }

            var n = new byte[newLen];
            int p = 0;
            while (p < newLen)
            {
                int op = gz.ReadByte();
                if (op < 0) break;
                if (op == 0) { long off = ReadVar(gz), len = ReadVar(gz); Array.Copy(o, off, n, p, len); p += (int)len; }
                else { long len = ReadVar(gz); ReadFull(gz, n, p, (int)len); p += (int)len; }
            }
            if (Hex(Sha1(n)) != Hex(newHash)) { Console.Error.WriteLine("补丁结果校验失败"); return 3; }
            File.WriteAllBytes(outPath, n);
        }
        return 0;
    }

    static void ReadFull(Stream s, byte[] buf, int count) { ReadFull(s, buf, 0, count); }
    static void ReadFull(Stream s, byte[] buf, int off, int count)
    {
        int got = 0;
        while (got < count) { int r = s.Read(buf, off + got, count - got); if (r <= 0) throw new EndOfStreamException(); got += r; }
    }

    public static int Main(string[] args)
    {
        try
        {
            if (args.Length == 4 && args[0] == "create") { Create(args[1], args[2], args[3]); Console.WriteLine("delta -> " + args[3] + "  (" + new FileInfo(args[3]).Length / 1024 + " KB)"); return 0; }
            if (args.Length == 4 && args[0] == "apply") return Apply(args[1], args[2], args[3]);
            Console.Error.WriteLine("用法: BinDelta create <旧> <新> <补丁>\n      BinDelta apply  <旧> <补丁> <输出>");
            return 1;
        }
        catch (Exception e) { Console.Error.WriteLine("错误: " + e.Message); return 4; }
    }
}
