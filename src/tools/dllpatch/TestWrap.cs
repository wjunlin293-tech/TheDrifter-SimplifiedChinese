// 用近似字宽（汉字=1，拉丁=0.5）跑真实译文，检查断行结果与避头尾。
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

public static class TestWrap
{
    static float Measure(string s)
    {
        s = Regex.Replace(s, "<[^>]+>", "");
        float w = 0;
        foreach (char c in s) w += (c >= 0x2E80) ? 1f : 0.5f;
        return w;
    }

    public static void Main(string[] args)
    {
        string csv = args[0];
        float width = float.Parse(args[1]);
        var lines = new List<string>();
        using (var sr = new StreamReader(csv, new UTF8Encoding(true)))
        {
            string all = sr.ReadToEnd();
            foreach (Match m in Regex.Matches(all, "\n[^\n]*$", RegexOptions.None)) { }
            // 简易 CSV 解析，取最后一列
            int i = 0; var row = new List<string>(); var cur = new StringBuilder(); bool q = false;
            while (i < all.Length)
            {
                char c = all[i];
                if (q) { if (c == '"') { if (i + 1 < all.Length && all[i + 1] == '"') { cur.Append('"'); i++; } else q = false; } else cur.Append(c); }
                else if (c == '"') q = true;
                else if (c == ',') { row.Add(cur.ToString()); cur.Length = 0; }
                else if (c == '\n') { row.Add(cur.ToString()); cur.Length = 0; if (row.Count >= 6) lines.Add(row[5]); row.Clear(); }
                else if (c != '\r') cur.Append(c);
                i++;
            }
        }
        int over = 0, wrapped = 0, bad = 0;
        string noStart = "，。、；：？！）】》〕」』”’…";
        foreach (string t in lines)
        {
            if (string.IsNullOrEmpty(t)) continue;
            string w = CjkWrap.Wrap(t, width, Measure);
            string[] ls = w.Split('\n');
            if (ls.Length > 1) wrapped++;
            foreach (string l in ls)
            {
                if (Measure(l) > width + 0.01f) { if (over++ < 5) Console.WriteLine("OVER(" + Measure(l) + "): " + l); }
                if (l.Length > 0 && noStart.IndexOf(l[0]) >= 0) { if (bad++ < 5) Console.WriteLine("BADSTART: " + l); }
            }
        }
        Console.WriteLine("lines=" + lines.Count + " wrapped=" + wrapped + " overflow=" + over + " badstart=" + bad);
        string demo = "他声称是被三一陷害的，连苍蝇都不会伤害。行吧（测试）——这是<color=#ff0000ff>一段带标记</color>的长文本，用来检查断行和避头尾是否正常工作。";
        Console.WriteLine("--- demo width=" + width + " ---");
        Console.WriteLine(CjkWrap.Wrap(demo, width, Measure));
    }
}
