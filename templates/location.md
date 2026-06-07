---
# Source of truth for identity/aliases/hierarchy/images. config/*.yaml are
# GENERATED from these blocks by scripts/build_index.py — do not hand-edit them.
id: [location-slug]
type: location
name: [LOCATION NAME]
aliases: []      # alternative names this location is referred to by
# part_of: [parent-id]   # optional: id of the location/region this sits inside
# contains:              # optional: page-less sub-locations folded to this page.
#   - id: [sub-slug]     #   Each is mirrored by a `## [[Name]]` section in the body
#     name: [Sub Name]   #   and resolves to this page until promoted to its own file.
#     aliases: []
# images:                # optional; mirrors a config/image-map.yaml entry. Put a
#                        # `subjects: [sub-slug]` on an image to make a page-less
#                        # sub-location discoverable as a reference.
---
# [LOCATION NAME]

**Type:** City | Town | Wilderness | Building | Region
**First Visited:** [[Session X]]

## Description
[What the place looks like, feels like]

## Notable Features
- [Feature 1]
- [Feature 2]

## Connected Locations
- [[Location]] - [Relationship/direction]

## Associated NPCs
- [[NPC Name]] - [Their connection to this place]

## Events Here
- [[Session X]] - [What happened]
