<#
.SYNOPSIS
一键应用信工本科生毕业论文（设计）Word 排版格式。

.DESCRIPTION
本脚本使用 Microsoft Word COM 自动化接口处理 .docx 文件。
默认不会覆盖原文件，而是在同目录生成“原文件名_格式化.docx”。

.PARAMETER Path
需要排版的 Word 文件路径，支持 .docx。

.PARAMETER OutputPath
可选。指定格式化后另存为的文件路径。

.PARAMETER Overwrite
可选。直接覆盖原文件。未指定 OutputPath 时才生效。

.PARAMETER Visible
可选。让 Word 在执行过程中可见，便于排查问题。

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\lab\scripts\Apply-ThesisWordFormat.ps1 -Path .\lab\论文.docx

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\lab\scripts\Apply-ThesisWordFormat.ps1 -Path .\lab\论文.docx -OutputPath .\lab\论文_最终版.docx

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\lab\scripts\Apply-ThesisWordFormat.ps1 -Path .\lab\论文.docx -Overwrite
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$Path,

    [string]$OutputPath = "",

    [switch]$Overwrite,

    [switch]$Visible
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-CmToPoint {
    param([double]$Cm)
    return $Cm * 28.3464566929
}

function Set-CjkLatinFont {
    param(
        [Parameter(Mandatory = $true)]$Font,
        [string]$Cjk = "宋体",
        [string]$Latin = "Times New Roman",
        [double]$Size = 12,
        [bool]$Bold = $false
    )

    $Font.NameFarEast = $Cjk
    $Font.NameAscii = $Latin
    $Font.NameOther = $Latin
    $Font.Name = $Latin
    $Font.Size = $Size
    $Font.Bold = if ($Bold) { -1 } else { 0 }
}

function Set-ParagraphCommon {
    param(
        [Parameter(Mandatory = $true)]$ParagraphFormat,
        [int]$Alignment = 3,
        [int]$LineSpacingRule = 4,
        [double]$LineSpacing = 22,
        [double]$SpaceBefore = 0,
        [double]$SpaceAfter = 0
    )

    $ParagraphFormat.Alignment = $Alignment
    $ParagraphFormat.LineSpacingRule = $LineSpacingRule
    if ($LineSpacingRule -eq 4) {
        $ParagraphFormat.LineSpacing = $LineSpacing
    }
    $ParagraphFormat.SpaceBefore = $SpaceBefore
    $ParagraphFormat.SpaceAfter = $SpaceAfter
}

function Set-BuiltinStyle {
    param(
        [Parameter(Mandatory = $true)]$Document,
        [Parameter(Mandatory = $true)][int]$StyleId,
        [string]$CjkFont,
        [double]$Size,
        [bool]$Bold,
        [int]$Alignment,
        [int]$LineSpacingRule,
        [double]$LineSpacing,
        [double]$SpaceBefore,
        [double]$SpaceAfter
    )

    $style = $Document.Styles.Item($StyleId)
    Set-CjkLatinFont -Font $style.Font -Cjk $CjkFont -Size $Size -Bold $Bold
    Set-ParagraphCommon `
        -ParagraphFormat $style.ParagraphFormat `
        -Alignment $Alignment `
        -LineSpacingRule $LineSpacingRule `
        -LineSpacing $LineSpacing `
        -SpaceBefore $SpaceBefore `
        -SpaceAfter $SpaceAfter
}

$sourcePath = (Resolve-Path -LiteralPath $Path).Path
$sourceItem = Get-Item -LiteralPath $sourcePath

if ($sourceItem.Extension -notin @(".docx", ".doc")) {
    throw "仅支持 Word 文件：.docx 或 .doc。当前文件：$($sourceItem.Name)"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    if ($Overwrite) {
        $targetPath = $sourcePath
    }
    else {
        $targetPath = Join-Path $sourceItem.DirectoryName ("{0}_格式化{1}" -f $sourceItem.BaseName, $sourceItem.Extension)
    }
}
else {
    $targetPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
}

if ($targetPath -ne $sourcePath) {
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
}

# Word constants
$wdPaperA4 = 7
$wdOrientPortrait = 0
$wdGutterPosLeft = 0
$wdHeaderFooterPrimary = 1
$wdAlignParagraphLeft = 0
$wdAlignParagraphCenter = 1
$wdAlignParagraphJustify = 3
$wdAlignPageNumberCenter = 1
$wdLineSpace1pt5 = 1
$wdLineSpaceExactly = 4
$wdStyleNormal = -1
$wdStyleHeading1 = -2
$wdStyleHeading2 = -3
$wdStyleHeading3 = -4
$wdFormatDocumentDefault = 16

$word = $null
$doc = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = [bool]$Visible
    $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($targetPath)

    # 页面设置：A4、页边距、页眉页脚、装订线
    foreach ($section in $doc.Sections) {
        $page = $section.PageSetup
        $page.PaperSize = $wdPaperA4
        $page.Orientation = $wdOrientPortrait
        $page.TopMargin = Convert-CmToPoint 2.5
        $page.BottomMargin = Convert-CmToPoint 2.5
        $page.LeftMargin = Convert-CmToPoint 2
        $page.RightMargin = Convert-CmToPoint 2
        $page.HeaderDistance = Convert-CmToPoint 1.8
        $page.FooterDistance = Convert-CmToPoint 2
        $page.Gutter = Convert-CmToPoint 0.5
        $page.GutterPos = $wdGutterPosLeft

        $headerRange = $section.Headers.Item($wdHeaderFooterPrimary).Range
        $headerRange.Text = "中央民族大学本科生毕业论文（设计）"
        Set-CjkLatinFont -Font $headerRange.Font -Cjk "宋体" -Size 10.5 -Bold $false
        $headerRange.Font.Spacing = 0.5
        $headerRange.ParagraphFormat.Alignment = $wdAlignParagraphCenter

        $footer = $section.Footers.Item($wdHeaderFooterPrimary)
        $footer.Range.Text = ""
        [void]$footer.PageNumbers.Add($wdAlignPageNumberCenter, $true)
        Set-CjkLatinFont -Font $footer.Range.Font -Cjk "宋体" -Size 10.5 -Bold $false
        $footer.Range.ParagraphFormat.Alignment = $wdAlignParagraphCenter
    }

    # 样式设置
    Set-BuiltinStyle -Document $doc -StyleId $wdStyleNormal -CjkFont "宋体" -Size 12 -Bold $false `
        -Alignment $wdAlignParagraphJustify -LineSpacingRule $wdLineSpaceExactly -LineSpacing 22 -SpaceBefore 0 -SpaceAfter 0

    Set-BuiltinStyle -Document $doc -StyleId $wdStyleHeading1 -CjkFont "黑体" -Size 16 -Bold $true `
        -Alignment $wdAlignParagraphCenter -LineSpacingRule $wdLineSpace1pt5 -LineSpacing 18 -SpaceBefore 12 -SpaceAfter 12

    Set-BuiltinStyle -Document $doc -StyleId $wdStyleHeading2 -CjkFont "黑体" -Size 14 -Bold $true `
        -Alignment $wdAlignParagraphLeft -LineSpacingRule $wdLineSpace1pt5 -LineSpacing 18 -SpaceBefore 0 -SpaceAfter 0

    Set-BuiltinStyle -Document $doc -StyleId $wdStyleHeading3 -CjkFont "黑体" -Size 12 -Bold $true `
        -Alignment $wdAlignParagraphLeft -LineSpacingRule $wdLineSpace1pt5 -LineSpacing 18 -SpaceBefore 0 -SpaceAfter 0

    # 按标题文本重新套用标题样式，适合从 Markdown 转 Word 后样式丢失的情况。
    $inReferences = $false
    foreach ($paragraph in $doc.Paragraphs) {
        $text = $paragraph.Range.Text -replace "[`r`a]", ""
        $text = $text.Trim()
        if ([string]::IsNullOrWhiteSpace($text)) {
            continue
        }

        if ($text -match "^(摘要|Abstract|参考文献|附录)$" -or $text -match "^第\d+章\s+") {
            $paragraph.Range.Style = $doc.Styles.Item($wdStyleHeading1)
            $inReferences = ($text -eq "参考文献")
            continue
        }

        if ($text -match "^\d+\.\d+\.\d+\s+") {
            $paragraph.Range.Style = $doc.Styles.Item($wdStyleHeading3)
            continue
        }

        if ($text -match "^\d+\.\d+\s+") {
            $paragraph.Range.Style = $doc.Styles.Item($wdStyleHeading2)
            continue
        }

        if ($text -match "^(图|表)\d+-\d+\s+") {
            Set-CjkLatinFont -Font $paragraph.Range.Font -Cjk "宋体" -Size 10.5 -Bold $true
            Set-ParagraphCommon -ParagraphFormat $paragraph.Range.ParagraphFormat `
                -Alignment $wdAlignParagraphCenter `
                -LineSpacingRule $wdLineSpaceExactly `
                -LineSpacing 22 `
                -SpaceBefore 0 `
                -SpaceAfter 0
            continue
        }

        if ($inReferences -or $text -match "^\[\d+\]") {
            Set-CjkLatinFont -Font $paragraph.Range.Font -Cjk "宋体" -Size 12 -Bold $false
            Set-ParagraphCommon -ParagraphFormat $paragraph.Range.ParagraphFormat `
                -Alignment $wdAlignParagraphLeft `
                -LineSpacingRule $wdLineSpaceExactly `
                -LineSpacing 22 `
                -SpaceBefore 0 `
                -SpaceAfter 0
            continue
        }

        # 正文段落
        Set-CjkLatinFont -Font $paragraph.Range.Font -Cjk "宋体" -Size 12 -Bold $false
        Set-ParagraphCommon -ParagraphFormat $paragraph.Range.ParagraphFormat `
            -Alignment $wdAlignParagraphJustify `
            -LineSpacingRule $wdLineSpaceExactly `
            -LineSpacing 22 `
            -SpaceBefore 0 `
            -SpaceAfter 0
    }

    # 表格居中，表格正文使用小五/五号较常见；若学校另有模板，可在 Word 中微调。
    foreach ($table in $doc.Tables) {
        $table.Rows.Alignment = 1
        Set-CjkLatinFont -Font $table.Range.Font -Cjk "宋体" -Size 10.5 -Bold $false
        $table.Range.ParagraphFormat.Alignment = $wdAlignParagraphCenter
        $table.Range.ParagraphFormat.SpaceBefore = 0
        $table.Range.ParagraphFormat.SpaceAfter = 0
    }

    $doc.SaveAs2($targetPath, $wdFormatDocumentDefault)
    Write-Host "格式已应用：$targetPath"
}
finally {
    if ($null -ne $doc) {
        $doc.Close($true) | Out-Null
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null
    }
    if ($null -ne $word) {
        $word.Quit() | Out-Null
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
