import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"

const explorerOptions = {
  folderClickBehavior: "link" as const,
  folderDefaultState: "collapsed" as const,
  sortFn: (a: any, b: any) => {
    const ARC_ORDER: Record<string, number> = {
      "forgotten-and-forsaken": 1,
      "curse-of-ruin": 2,
    }
    const aOrder = ARC_ORDER[a.slugSegment]
    const bOrder = ARC_ORDER[b.slugSegment]
    if (aOrder !== undefined && bOrder !== undefined) {
      return aOrder - bOrder
    }
    if (!a.isFolder && !b.isFolder) {
      const aMatch = a.slugSegment?.match(/^session-(\d+)$/)
      const bMatch = b.slugSegment?.match(/^session-(\d+)$/)
      if (aMatch && bMatch) {
        return parseInt(bMatch[1], 10) - parseInt(aMatch[1], 10)
      }
    }
    if ((!a.isFolder && !b.isFolder) || (a.isFolder && b.isFolder)) {
      return a.displayName.localeCompare(b.displayName, undefined, {
        numeric: true,
        sensitivity: "base",
      })
    }
    return !a.isFolder && b.isFolder ? 1 : -1
  },
}

export const sharedPageComponents: SharedLayout = {
  head: Component.Head(),
  header: [],
  afterBody: [],
  footer: Component.Footer({
    links: {},
  }),
}

export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    Component.ConditionalRender({
      component: Component.Breadcrumbs(),
      condition: (page) => page.fileData.slug !== "index",
    }),
    Component.ArticleTitle(),
    Component.ContentMeta(),
    Component.TagList(),
  ],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        {
          Component: Component.Search(),
          grow: true,
        },
        { Component: Component.Darkmode() },
      ],
    }),
    Component.Explorer(explorerOptions),
  ],
  right: [
    Component.Graph(),
    Component.DesktopOnly(Component.TableOfContents()),
    Component.Backlinks(),
  ],
}

export const defaultListPageLayout: PageLayout = {
  beforeBody: [Component.Breadcrumbs(), Component.ArticleTitle(), Component.ContentMeta()],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        {
          Component: Component.Search(),
          grow: true,
        },
        { Component: Component.Darkmode() },
      ],
    }),
    Component.Explorer(explorerOptions),
  ],
  right: [],
}
