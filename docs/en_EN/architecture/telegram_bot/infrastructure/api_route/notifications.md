# 📜 Notifications

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module provides the `NotificationsApiProvider` class, an implementation of the `NotificationsDataProvider` protocol that interacts with an external API for managing notifications. It leverages the `BaseApiClient` for making HTTP requests.

## `NotificationsApiProvider` Class

The `NotificationsApiProvider` acts as a client for the backend's notifications API, offering CRUD (Create, Read, Update, Delete) operations for notification data.

### Initialization (`__init__`)

```python
def __init__(self, api_client: BaseApiClient, resource_path: str = "/notifications"):
```
Initializes the `NotificationsApiProvider`.

*   `api_client` (`BaseApiClient`): An instance of `BaseApiClient` used to perform HTTP requests to the external API.
*   `resource_path` (`str`): The base path for the notifications resource on the API (default: `"/notifications"`).

### `get_data` Method

```python
async def get_data(self, user_id: int) -> Any:
```
Retrieves notification data for a specific user from the API.

*   `user_id` (`int`): The ID of the user for whom to fetch notification data.

**Process:**
*   Sends a `GET` request to the API endpoint `/{resource_path}/{user_id}`.

**Returns:**
`Any`: The data received from the API.

### `create_notification` Method

```python
async def create_notification(self, user_id: int, data: dict) -> Any:
```
Creates a new notification for a user via the API.

*   `user_id` (`int`): The ID of the user for whom to create the notification.
*   `data` (`dict`): A dictionary containing the notification data to be sent in the request body.

**Process:**
*   Sends a `POST` request to the API endpoint `/{resource_path}/{user_id}` with the `data` as JSON payload.

**Returns:**
`Any`: The response from the API after creating the notification.

### `update_notification` Method

```python
async def update_notification(self, notification_id: int, data: dict) -> Any:
```
Updates an existing notification via the API.

*   `notification_id` (`int`): The ID of the notification to update.
*   `data` (`dict`): A dictionary containing the updated notification data to be sent in the request body.

**Process:**
*   Sends a `PUT` (or `PATCH`, depending on API design) request to the API endpoint `/{resource_path}/{notification_id}` with the `data` as JSON payload.

**Returns:**
`Any`: The response from the API after updating the notification.

### `delete_notification` Method

```python
async def delete_notification(self, notification_id: int) -> None:
```
Deletes a notification via the API.

*   `notification_id` (`int`): The ID of the notification to delete.

**Process:**
*   Sends a `DELETE` request to the API endpoint `/{resource_path}/{notification_id}`.

**Returns:**
`None`: This method typically does not return content on successful deletion.
