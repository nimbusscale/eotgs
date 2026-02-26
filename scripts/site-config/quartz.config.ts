import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"

const config: QuartzConfig = {
  configuration: {
    pageTitle: "Echoes of the Godstorm",
    pageTitleSuffix: " | Grimwild",
    enableSPA: true,
    enablePopovers: true,
    analytics: null,
    locale: "en-US",
    baseUrl: "foundry.jjk3.com/echoes-of-the-godstorm",
    ignorePatterns: ["private", "templates", ".obsidian"],
    defaultDateType: "modified",
    theme: {
      fontOrigin: "googleFonts",
      cdnCaching: true,
      typography: {
        header: "Cinzel",
        body: "Lora",
        code: "IBM Plex Mono",
      },
      colors: {
        lightMode: {
          light: "#faf6ee",
          lightgray: "#e8e0d0",
          gray: "#9e9585",
          darkgray: "#3d3528",
          dark: "#1a1510",
          secondary: "#8b6914",
          tertiary: "#b8860b",
          highlight: "rgba(184, 134, 11, 0.12)",
          textHighlight: "#ffd70044",
        },
        darkMode: {
          light: "#1a1510",
          lightgray: "#2e2820",
          gray: "#6e6355",
          darkgray: "#d4c9b0",
          dark: "#f0e6d0",
          secondary: "#d4a843",
          tertiary: "#b8860b",
          highlight: "rgba(184, 134, 11, 0.15)",
          textHighlight: "#ffd70033",
        },
      },
    },
  },
  plugins: {
    transformers: [
      Plugin.FrontMatter(),
      Plugin.CreatedModifiedDate({
        priority: ["frontmatter", "filesystem"],
      }),
      Plugin.ObsidianFlavoredMarkdown({ enableInHtmlEmbed: false }),
      Plugin.GitHubFlavoredMarkdown(),
      Plugin.TableOfContents(),
      Plugin.CrawlLinks({ markdownLinkResolution: "shortest" }),
      Plugin.Description(),
    ],
    filters: [Plugin.RemoveDrafts()],
    emitters: [
      Plugin.AliasRedirects(),
      Plugin.ComponentResources(),
      Plugin.ContentPage(),
      Plugin.FolderPage(),
      Plugin.TagPage(),
      Plugin.ContentIndex({
        enableSiteMap: true,
        enableRSS: false,
      }),
      Plugin.Assets(),
      Plugin.Static(),
      Plugin.Favicon(),
      Plugin.NotFoundPage(),
    ],
  },
}

export default config
