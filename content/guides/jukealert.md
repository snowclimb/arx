---
title: JukeAlert
slug: jukealert
category: Core Mechanics
order: 4
description: Learn how snitches detect players and how jukebox snitches record activity around important areas.
source_url: https://civmc.net/wiki/plugins/unique/jukealert
source_label: Official CivMC Wiki — JukeAlert
reviewed: 2026-08-15
---

JukeAlert provides CivMC's surveillance mechanic. Reinforced note blocks and jukeboxes become **snitches** tied to the NameLayer group they are reinforced to.

## Note block snitches

A note block snitch reports players entering or joining inside its field. It is useful for live alerts but doesn't retain the same detailed history as a jukebox.

## Jukebox snitches

Jukebox snitches also log interactions such as block breaks and opening containers/doors. You can use `/jainfo` and `/ja` to review a nearby jukebox's information, and `/jalist` for viewing snitches you can access.

## Naming and maintenance

Use `/janame [name]` to rename a snitch while standing within its range. Snitches can also become dormant when not refreshed, so it's important to monitor infrastructure for occasional maintenance.

## Arx advice

Assume important government areas are monitored. Do not break or alter snitches you do not own, and keep sensitive snitch groups separate from broad public access namelayers.
