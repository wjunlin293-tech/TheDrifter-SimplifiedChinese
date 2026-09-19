// 用 Mono.Cecil 把 TextWrapper.WrapText / WrapTextNicerInternal 的方法体换成对 CjkWrap 的调用。
using System;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

public static class Patcher
{
    public static int Main(string[] args)
    {
        string managed = args[0];     // Managed 目录（读取原版 DLL 的目录，也是 CjkWrap.dll 所在位置）
        string src = args[1];         // 原版 Assembly-CSharp-firstpass.dll
        string dst = args[2];         // 输出
        string helper = args[3];      // CjkWrap.dll

        DefaultAssemblyResolver res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(managed);
        ReaderParameters rp = new ReaderParameters { AssemblyResolver = res };
        AssemblyDefinition asm = AssemblyDefinition.ReadAssembly(src, rp);
        ModuleDefinition mod = asm.MainModule;

        AssemblyDefinition h = AssemblyDefinition.ReadAssembly(helper);
        TypeDefinition ht = h.MainModule.GetType("CjkWrap");
        MethodReference wrap = mod.ImportReference(ht.Methods.First(m => m.Name == "Wrap"));
        MethodReference wrapCount = mod.ImportReference(ht.Methods.First(m => m.Name == "WrapCount"));

        // 用游戏自己的 mscorlib 里的 Func<string,float>
        AssemblyNameReference corlib = mod.AssemblyReferences.First(a => a.Name == "mscorlib");
        AssemblyDefinition corlibDef = res.Resolve(corlib);
        TypeDefinition funcDef = corlibDef.MainModule.GetType("System.Func`2");
        GenericInstanceType funcInst = new GenericInstanceType(mod.ImportReference(funcDef));
        funcInst.GenericArguments.Add(mod.TypeSystem.String);
        funcInst.GenericArguments.Add(mod.TypeSystem.Single);
        MethodDefinition funcCtorDef = funcDef.Methods.First(m => m.IsConstructor && !m.IsStatic);
        MethodReference funcCtor = new MethodReference(".ctor", mod.TypeSystem.Void, funcInst) { HasThis = true };
        foreach (ParameterDefinition p in funcCtorDef.Parameters)
            funcCtor.Parameters.Add(new ParameterDefinition(mod.ImportReference(p.ParameterType)));

        TypeDefinition tw = mod.GetType("PowerTools", "TextWrapper");
        MethodDefinition getWidth = tw.Methods.First(m => m.Name == "GetTextWidth");
        MethodDefinition wrapText = tw.Methods.First(m => m.Name == "WrapText");
        MethodDefinition nicer = tw.Methods.First(m => m.Name == "WrapTextNicerInternal");

        // WrapText(string input, float width) -> CjkWrap.Wrap(input, width, this.GetTextWidth)
        Reset(wrapText);
        ILProcessor il = wrapText.Body.GetILProcessor();
        il.Emit(OpCodes.Ldarg_1);
        il.Emit(OpCodes.Ldarg_2);
        il.Emit(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldftn, getWidth);
        il.Emit(OpCodes.Newobj, funcCtor);
        il.Emit(OpCodes.Call, wrap);
        il.Emit(OpCodes.Ret);

        // WrapTextNicerInternal(string input, float width, out int numLines) -> CjkWrap.WrapCount(...)
        Reset(nicer);
        il = nicer.Body.GetILProcessor();
        il.Emit(OpCodes.Ldarg_1);
        il.Emit(OpCodes.Ldarg_2);
        il.Emit(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldftn, getWidth);
        il.Emit(OpCodes.Newobj, funcCtor);
        il.Emit(OpCodes.Ldarg_3);
        il.Emit(OpCodes.Call, wrapCount);
        il.Emit(OpCodes.Ret);

        asm.Write(dst);
        Console.WriteLine("patched -> " + dst);
        return 0;
    }

    private static void Reset(MethodDefinition m)
    {
        m.Body.Instructions.Clear();
        m.Body.Variables.Clear();
        m.Body.ExceptionHandlers.Clear();
        m.Body.InitLocals = false;
    }
}
