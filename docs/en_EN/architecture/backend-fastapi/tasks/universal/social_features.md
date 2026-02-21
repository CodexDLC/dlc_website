# 💡 Feature: Social Mechanics (Likes & Comments)

[⬅️ Back](../../README.md) | [🏠 Docs Root](../../../../../README.md)

**Status:** 💡 Idea / Backlog
**Priority:** Medium
**Phase:** Future (v2.0)

## 📝 Description

Transforming service from simple hosting to a social platform. Users should be able to rate content.

## 🎯 Goals

1.  Increase Engagement.
2.  Sort feed by popularity (Trending).

## 📋 Implementation Plan

### 1. Database

*   Table `likes`:
    *   `user_id` (FK -> users)
    *   `image_id` (FK -> images)
    *   `created_at`
    *   Unique Constraint: `(user_id, image_id)` (one like per image).

### 2. Backend API

*   `POST /media/{id}/like` — Like.
*   `DELETE /media/{id}/like` — Unlike.
*   Update `ImageRead` schema:
    *   `likes_count: int` (aggregation).
    *   `is_liked: bool` (personalized field, requires `current_user`).

## ❓ Questions

*   Do we need dislikes?
*   Do we need comments?
