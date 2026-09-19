// CJK 感知换行：原版 TextWrapper 只在空格处断行，中文整句会被当成一个词而溢出屏幕。
// 这里允许在汉字之间断行，并做基本的避头尾处理。编译为 CjkWrap.dll，由 Patcher 接进 TextWrapper。
using System;
using System.Collections.Generic;
using System.Text;

public static class CjkWrap
{
    private class Atom
    {
        public string Text = "";
        public bool Latin;
        public bool SpaceBefore;
        public bool GlueNext;
    }

    private const string NoStart = "，。、；：？！）】》〕」』”’…—～·％%,.;:!?)]}";
    private const string OpenBr = "（【《〔「『“‘([{";

    private static bool IsBreakable(char c)
    {
        return c >= 0x2E80 || c == 0x2026 || c == 0x2014 || c == 0x00B7 || (c >= 0x2018 && c <= 0x201D);
    }

    private static List<Atom> Atomize(string word, bool spaceBeforeFirst)
    {
        List<Atom> atoms = new List<Atom>();
        StringBuilder pendingTag = new StringBuilder();
        bool first = true;
        for (int i = 0; i < word.Length; i++)
        {
            char c = word[i];
            if (c == '<')
            {
                int end = word.IndexOf('>', i);
                if (end > i)
                {
                    string tag = word.Substring(i, end - i + 1);
                    if (atoms.Count > 0 && tag.StartsWith("</")) atoms[atoms.Count - 1].Text += tag;
                    else pendingTag.Append(tag);
                    i = end;
                    continue;
                }
            }
            Atom last = atoms.Count > 0 ? atoms[atoms.Count - 1] : null;
            bool glue = last != null && last.GlueNext;
            if (last != null && NoStart.IndexOf(c) >= 0 && pendingTag.Length == 0)
            {
                last.Text += c;
                continue;
            }
            bool breakable = IsBreakable(c);
            if (last != null && !breakable && last.Latin && !glue && pendingTag.Length == 0)
            {
                last.Text += c;
                continue;
            }
            if (last != null && glue)
            {
                last.Text += pendingTag.ToString() + c;
                pendingTag.Length = 0;
                last.GlueNext = false;
                if (OpenBr.IndexOf(c) >= 0) last.GlueNext = true;
                if (!breakable) last.Latin = true;
                continue;
            }
            Atom a = new Atom();
            a.Text = pendingTag.ToString() + c;
            pendingTag.Length = 0;
            a.Latin = !breakable;
            a.SpaceBefore = first && spaceBeforeFirst;
            a.GlueNext = OpenBr.IndexOf(c) >= 0;
            atoms.Add(a);
            first = false;
        }
        if (pendingTag.Length > 0)
        {
            if (atoms.Count > 0) atoms[atoms.Count - 1].Text += pendingTag.ToString();
            else { Atom a = new Atom(); a.Text = pendingTag.ToString(); a.Latin = true; a.SpaceBefore = spaceBeforeFirst; atoms.Add(a); }
        }
        return atoms;
    }

    public static string WrapCount(string input, float width, Func<string, float> measure, out int numLines)
    {
        string[] lines = input.Split('\n');
        numLines = lines.Length;
        if (width <= 0f) return input;
        StringBuilder result = new StringBuilder();
        numLines = 0;
        for (int li = 0; li < lines.Length; li++)
        {
            numLines++;
            if (li > 0) result.Append("\n");
            string[] words = lines[li].Split(' ');
            List<Atom> atoms = new List<Atom>();
            for (int w = 0; w < words.Length; w++)
                atoms.AddRange(Atomize(words[w], w > 0));
            string cur = "";
            for (int k = 0; k < atoms.Count; k++)
            {
                Atom a = atoms[k];
                string cand = cur.Length == 0 ? a.Text : (a.SpaceBefore ? cur + " " + a.Text : cur + a.Text);
                if (cur.Length > 0 && measure(cand) > width)
                {
                    result.Append(cur).Append("\n");
                    numLines++;
                    cur = a.Text;
                }
                else
                {
                    cur = cand;
                }
            }
            result.Append(cur);
        }
        return result.ToString();
    }

    public static string Wrap(string input, float width, Func<string, float> measure)
    {
        int n;
        return WrapCount(input, width, measure, out n);
    }
}
