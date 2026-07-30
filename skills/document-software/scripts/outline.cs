#:package Microsoft.CodeAnalysis.CSharp@4.14.0
// Outline of C# sources for writing a reference: types, members, constants and the first line of their XML doc.
// Usage: dotnet run outline.cs -- <file or directory> [...]
using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

var skipped = new[] { "bin", "obj", ".git", "node_modules" };
var files = args.SelectMany(path => Directory.Exists(path)
        ? Directory.EnumerateFiles(path, "*.cs", SearchOption.AllDirectories)
            .Where(f => !f.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar).Any(skipped.Contains))
        : [path])
    .Order();
Console.OutputEncoding = System.Text.Encoding.UTF8;
foreach (var file in files)
{
    var root = CSharpSyntaxTree.ParseText(File.ReadAllText(file)).GetCompilationUnitRoot();
    Console.WriteLine($"## {file.Replace('\\', '/')}");
    foreach (var type in root.DescendantNodes().OfType<BaseTypeDeclarationSyntax>())
    {
        var line = type.GetLocation().GetLineSpan().StartLinePosition.Line + 1;
        var kind = type switch
        {
            RecordDeclarationSyntax r => r.ClassOrStructKeyword.Text is "" ? "record" : $"record {r.ClassOrStructKeyword.Text}",
            TypeDeclarationSyntax t => t.Keyword.Text,
            EnumDeclarationSyntax => "enum",
            _ => "type",
        };
        var parameters = type is TypeDeclarationSyntax { ParameterList: { } primary } ? Flat(primary.ToString()) : "";
        var bases = type.BaseList is null ? "" : " : " + string.Join(", ", type.BaseList.Types.Select(b => Flat(b.ToString())));
        Console.WriteLine($"  {line}: {Modifiers(type.Modifiers)}{kind} {type.Identifier.Text}{(type as TypeDeclarationSyntax)?.TypeParameterList}{parameters}{bases}{Doc(type)}");
        if (type is EnumDeclarationSyntax e)
        {
            Console.WriteLine($"    {string.Join(", ", e.Members.Select(m => Flat(m.ToString())))}");
            continue;
        }
        foreach (var member in ((TypeDeclarationSyntax)type).Members)
        {
            var text = member switch
            {
                FieldDeclarationSyntax f => $"{Modifiers(f.Modifiers)}{Flat(f.Declaration.ToString())}",
                PropertyDeclarationSyntax p => $"{Modifiers(p.Modifiers)}{Flat(p.Type.ToString())} {p.Identifier.Text} {Accessors(p)}{(p.Initializer is null ? "" : " " + Flat(p.Initializer.ToString()))}",
                ConstructorDeclarationSyntax c => $"{Modifiers(c.Modifiers)}{c.Identifier.Text}{Flat(c.ParameterList.ToString())}",
                MethodDeclarationSyntax m => $"{Modifiers(m.Modifiers)}{Flat(m.ReturnType.ToString())} {m.Identifier.Text}{m.TypeParameterList}{Flat(m.ParameterList.ToString())}",
                EventFieldDeclarationSyntax ev => $"{Modifiers(ev.Modifiers)}event {Flat(ev.Declaration.ToString())}",
                _ => null,
            };
            if (text is null) continue;
            var memberLine = member.GetLocation().GetLineSpan().StartLinePosition.Line + 1;
            Console.WriteLine($"    {memberLine}: {Cut(text, 160)}{Doc(member)}");
        }
    }
    Console.WriteLine();
}

static string Flat(string text) =>
    Regex.Replace(text, @"\s+", " ").Replace("( ", "(").Replace(" )", ")").Trim();

static string Cut(string text, int limit) => text.Length <= limit ? text : text[..limit] + "…";

static string Modifiers(SyntaxTokenList modifiers) =>
    string.Concat(modifiers.Where(m => !m.IsKind(SyntaxKind.PartialKeyword)).Select(m => m.Text + " "));

static string Accessors(PropertyDeclarationSyntax p) =>
    p.AccessorList is null ? "=> …" : "{ " + string.Join(" ", p.AccessorList.Accessors.Select(a => Modifiers(a.Modifiers) + a.Keyword.Text + ";")) + " }";

// First sentence of the <summary> of an XML doc comment, as "  # text".
static string Doc(SyntaxNode node)
{
    var doc = node.GetLeadingTrivia().Select(t => t.GetStructure()).OfType<DocumentationCommentTriviaSyntax>().FirstOrDefault();
    var summary = doc?.Content.OfType<XmlElementSyntax>().FirstOrDefault(x => x.StartTag.Name.ToString() == "summary");
    if (summary is null) return "";
    var text = Flat(string.Concat(summary.Content.Select(c => c.ToString())).Replace("///", " "));
    text = Regex.Replace(text, @"<(?:see cref|paramref name|typeparamref name)=""([^""]+)""\s*/>", "$1");
    text = Regex.Replace(text, @"</?c>", "`");
    text = System.Net.WebUtility.HtmlDecode(text);
    return text.Length == 0 ? "" : "  # " + Cut(text, 140);
}
