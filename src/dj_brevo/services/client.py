"""HTTP client for the Brevo API."""

from typing import Any, Literal

import httpx

from dj_brevo.exceptions import (
    BrevoAPIError,
    BrevoAuthError,
    BrevoConfigError,
    BrevoRateLimitError,
)
from dj_brevo.settings import brevo_settings


class BrevoClient:
    """Client for interacting with the Brevo API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the client.

        Args:
            api_key: Brevo API key. If not provided, reads from settings.
        """
        self.api_key = api_key or brevo_settings.API_KEY
        if not self.api_key:
            raise BrevoConfigError(
                "Brevo API key not configured."
                "Set DJ_BREVO['API_KEY'] in your Django settings"
            )
        self.base_url = brevo_settings.API_BASE_URL
        self.timeout = brevo_settings.TIMEOUT
        self.sandbox = brevo_settings.SANDBOX

    def _get_headers(self) -> dict[str, str]:
        """Returns headers required for Brevo API requests."""
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _apply_sandbox(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Add sandbox header to payload if sandbox mode is enabled.

        Args:
            payload: The API request payload.

        Returns:
            Payload with sandbox header added if enabled.
        """
        if self.sandbox:
            payload["headers"] = {"X-Sib-Sandbox": "drop"}
        return payload

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions.

        Args:
            response: The https response object.

        Returns:
            Parsed JSON response data.

        Raises:
            BrevoAuthError: If authentication failed (401).
            BrevoRateLimitError: If rate limit exceeded (429).
            BrevoAPIError: For other API errors (4xx, 5xx).
        """
        # Try to parse JSON
        try:
            data = response.json()
        except ValueError:
            data = {}

        # Success - return the data
        if response.is_success:
            return data  # type: ignore[no-any-return]

        # Map status codes to our exceptions
        message = data.get("message", response.text)

        if response.status_code == 401:
            raise BrevoAuthError(
                message=message,
                status_code=401,
                response_data=data,
            )
        elif response.status_code == 429:
            raise BrevoRateLimitError(
                message=message,
                status_code=429,
                response_data=data,
            )
        else:
            raise BrevoAPIError(
                message=message,
                status_code=response.status_code,
                response_data=data,
            )

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request to the Brevo API.

        Args:
            endpoint: API endpoint path (e.g., "/smtp/email").
            payload: JSON payload to send.

        Returns:
            Parsed JSON response.
        """
        url = f"{self.base_url}{endpoint}"

        response = httpx.post(
            url,
            json=payload,
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        return self._handle_response(response)

    def _get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request to the Brevo API.

        Args:
            endpoint: API endpoint path (e.g., "/contacts")
            params: Query parameters to send.

        Returns:
            Parsed JSON response
        """
        url = f"{self.base_url}{endpoint}"

        response = httpx.get(
            url,
            params=params,
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        return self._handle_response(response)

    def _put(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make a PUT request to the Brevo API.

        Args:
            endpoint: API endpoint path (e.g., "/contacts/{identifier}").
            payload: JSON payload to send.

        Returns:
            Parsed JSON response.
        """
        url = f"{self.base_url}{endpoint}"

        response = httpx.put(
            url,
            json=payload,
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        return self._handle_response(response)

    def _delete(self, endpoint: str) -> dict[str, Any]:
        """Make a DELETE request to the Brevo API.

        Args:
            endpoint: API endpoint path (e.g., "/contacts/{identifier}")

        Returns:
            Parsed JSON response
        """
        url = f"{self.base_url}{endpoint}"

        response = httpx.delete(
            url,
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        return self._handle_response(response)

    # region ############################### Email ############################

    def send_email(
        self,
        *,
        to: list[dict[str, str]],
        subject: str,
        html_content: str,
        sender: dict[str, str] | None = None,
        text_content: str | None = None,
        reply_to: dict[str, str] | None = None,
        cc: list[dict[str, str]] | None = None,
        bcc: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Send an email with HTML content you provide.

        Args:
              to: List of recipients, e.g., [{"email": "a@b.com", "name": "Name"}]
              subject: Email subject line.
              html_content: Rendered HTML body.
              sender: Sender info. Defaults to DJ_BREVO["DEFAULT_FROM_EMAIL"].
              text_content: Plain text version (optional).
              reply_to: Reply-to address (optional).
              cc: CC recipients (optional).
              bcc: BCC recipients (optional).

        Returns:
            API response with messageId.

        Example:
            client.send_email(
                to=[{"email": "user@example.com", "name": "David"}],
                subject="Welcome!",
                html_content="<html><body>Hello!</body></html>",
            )

        """
        if sender is None:
            default_email = brevo_settings.DEFAULT_FROM_EMAIL
            if not default_email:
                raise BrevoConfigError(
                    "No sender provided and DJ_BREVO['DEFAULT_FROM_EMAIL'] not set."
                )
            sender = {"email": default_email}

        payload: dict[str, Any] = {
            "sender": sender,
            "to": to,
            "subject": subject,
            "htmlContent": html_content,
        }

        if text_content:
            payload["textContent"] = text_content
        if reply_to:
            payload["replyTo"] = reply_to
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc

        return self._post("/smtp/email", self._apply_sandbox(payload))

    def send_template_email(
        self,
        *,
        to: list[dict[str, str]],
        template_id: int,
        params: dict[str, Any] | None = None,
        sender: dict[str, str] | None = None,
        reply_to: dict[str, str] | None = None,
        cc: list[dict[str, str]] | None = None,
        bcc: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Send an email using a Brevo template.

        Args:
            to: List of recipients, e.g., [{"email": "a@b.com", "name": "Name"}]
            template_id: ID of the template in Brevo.
            params: Template variables, e.g., {"firstName": "David"}.
            sender: Sender info (optional, can be set in Brevo template).
            reply_to: Reply-to address (optional).
            cc: CC recipients (optional).
            bcc: BCC recipients (optional).

        Returns:
            API response with messageId.

        Example:
            client.send_template_email(
                to=[{"email": "user@example.com"}],
                template_id=12,
                params={"firstName": "David", "orderTotal": "$50"},
            )
        """
        payload: dict[str, Any] = {
            "to": to,
            "templateId": template_id,
        }

        if params:
            payload["params"] = params
        if sender:
            payload["sender"] = sender
        if reply_to:
            payload["replyTo"] = reply_to
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc

        return self._post("/smtp/email", self._apply_sandbox(payload))

    # endregion

    # region ############################### Contacts #########################

    def create_contact(
        self,
        *,
        email: str,
        attributes: dict[str, Any] | None = None,
        list_ids: list[int] | None = None,
        update_enabled: bool = True,
    ) -> dict[str, Any]:
        """Create a contact in the Brevo API.

        Args:
            email: Email address of the user.
            attributes: Pass the set of attributes and their values.
                The attribute’s parameter should be passed in capital letter while
                creating a contact. Values that dont match the attribute type
                (e.g. text or string in a date attribute) will be ignored.
                These attributes must be present in your Brevo account.
                For eg: {“FNAME”:“Elly”, “COUNTRIES”: [“India”,“China”]}
            list_ids: Ids of the lists to add the contact to.
            update_enabled: Facilitate to update the existing contact in the same
                request (updateEnabled = true)

        Returns: Parsed JSON response.
        """
        payload: dict[str, Any] = {
            "email": email,
            "updateEnabled": update_enabled,
        }

        if attributes:
            payload["attributes"] = attributes
        if list_ids:
            payload["listIds"] = list_ids

        return self._post(
            "/contacts",
            payload,
        )

    def get_contact(
        self,
        identifier: str | int,
    ) -> dict[str, Any]:
        """Make a GET request for a contact from the Brevo API.

        Args:
            identifier: Email OR ID of the contact.

        Returns: Parsed JSON Response
        """

        return self._get(
            f"/contacts/{identifier}",
        )

    def update_contact(
        self,
        *,
        identifier: str | int,
        email: str | None = None,
        attributes: dict[str, Any] | None = None,
        list_ids: list[int] | None = None,
        unlink_list_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Update a contact in the Brevo API.

        Args:
            identifier: Email OR ID of the contact.
            email: Email address of the user.
            attributes: Pass the set of attributes and their values.
                The attribute’s parameter should be passed in capital letter while
                creating a contact. Values that dont match the attribute type
                (e.g. text or string in a date attribute) will be ignored.
                These attributes must be present in your Brevo account.
                For eg: {“FNAME”:“Elly”, “COUNTRIES”: [“India”,“China”]}
            list_ids: Ids of the lists to add the contact to.
            unlink_list_ids: Ids of the lists to remove the contact from.
        """
        payload: dict[str, Any] = {}

        if email:
            payload["email"] = email
        if list_ids:
            payload["listIds"] = list_ids
        if unlink_list_ids:
            payload["unlinkListIds"] = unlink_list_ids
        if attributes:
            payload["attributes"] = attributes

        return self._put(
            f"/contacts/{identifier}",
            payload=payload,
        )

    def list_contacts(
        self,
        list_ids: list[int] | None,
        limit: int = 50,
        offset: int = 0,
        sort: Literal["desc", "asc"] | None = None,
    ) -> dict[str, Any]:
        """Get a list of Contacts in a list(s).

        Args:
            list_ids: ds of the list. Either listIds or segmentId can be passed.
            limit: Number of documents per page.
            offset: Index of the first document of the page.
            sort: Sort the results in the ascending/descending order of record creation.
                Default order is descending if sort is not passed.
                Allowed values are `desc` and `asc`.
        """
        payload: dict[str, Any] = {}

        if list_ids:
            payload["listIds"] = list_ids
        if limit:
            payload["limit"] = limit
        if offset:
            payload["offset"] = offset
        if sort:
            payload["sort"] = sort

        return self._get(
            "/contacts",
            params=payload,
        )

    def add_contacts_to_list(
        self,
        list_id: int,
        emails: list[str],
    ) -> dict[str, Any]:
        """Add existing Brevo Contact(s) to a list.


        Args:
            list_id: ID of the list to add contacts to.
            emails: Email addresses OR IRs or EXT_ID attributes of the contacts.

        Returns:
            Parsed JSON response.
        """

        return self._post(
            f"/contacts/lists/{list_id}/contacts/add",
            payload={"emails": emails},
        )

    def remove_contacts_from_list(
        self,
        list_id: int,
        emails: list[str],
    ) -> dict[str, Any]:
        """Delete existing Brevo Contact(s) from a list.

        Args:
            list_id: ID of the list to remove contacts from.
            emails: Email addresses OR IRs or EXT_ID attributes of the contacts.

        Returns:
            Parsed JSON response.
        """

        return self._post(
            f"/contacts/lists/{list_id}/contacts/remove", payload={"emails": emails}
        )

    # endregion

    # region ############################### Lists ############################

    def get_lists(
        self,
        limit: int = 50,
        offset: int = 0,
        sort: Literal["desc", "asc"] = "desc",
    ) -> dict[str, Any]:
        """Gets a list of all Brevo Contact Lists from API.

        Args:
            limit: Number of documents per page
            offset: Index of the first document of the page
            sort: Sort the results in the ascending/descending order of record creation.
                Default order is descending if sort is not passed
                Allowed values: `asc`, `desc`

        Returns:
            Parsed JSON response.
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "sort": sort,
        }

        return self._get(
            "/contacts/lists",
            params,
        )

    def create_list(
        self,
        name: str,
        folder_id: int,
    ) -> dict[str, Any]:
        """Create a new list with Brevo API.

        Args:
            name (str): Name of the list.
            folder_id (int): Id of the parent folder which this list is to be created.

        Returns:
            Parsed JSON response.
        """
        return self._post(
            "/contacts/lists",
            {
                "folderId": folder_id,
                "name": name,
            },
        )

    def update_list(
        self,
        list_id: int,
        folder_id: int | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Updates a Brevo Contact List.

        Args:
            list_id: Id of the list to be updated.
            folder_id: Id of the folder in which the list is to be moved.
                Either of the two parameters (name, folderId) can be updated at a time.
            name: Name of the list. Either of the two parameters
                (name, folderId) can be updated at a time.

        Returns: Parsed JSON Response
        """
        payload: dict[str, Any] = {}

        if folder_id:
            payload["folderId"] = folder_id
        if name:
            payload["name"] = name

        return self._put(
            f"/contacts/lists/{list_id}",
            payload,
        )

    def delete_list(
        self,
        list_id: int,
    ) -> dict[str, Any]:
        """Delete a Brevo Contact list.

        Args:
            list_id: ID of the list.

        Returns:
            Parsed JSON list.
        """

        return self._delete(f"/contacts/lists/{list_id}")

    # endregion

    # region ############################## Attributes #######################

    def get_attributes(self) -> dict[str, Any]:
        """Get a list of all Brevo Contact Attributes.

        Returns: Parsed JSON Response
        """
        return self._get("/contacts/attributes")

    def create_attribute(
        self,
        attribute_name: str,
        attribute_category: Literal[
            "normal", "transactional", "category", "calculated", "global"
        ] = "normal",
        enumeration: list[dict[str, Any]] | None = None,
        is_recurring: bool | None = None,
        multi_category_options: list[str] | None = None,
        attribute_type: Literal[
            "text",
            "date",
            "float",
            "boolean",
            "id",
            "category",
            "multiple-choice",
            "user",
        ]
        | None = None,
        value: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Brevo Contact Attribute.

        Args:
            attribute_name: Name of the attribute.
            attribute_category: Category of the attribute
                Allowed values `normal`, `transactional`, `category`,
                `calculated`, `global`
            enumeration: List of values and labels that the attribute can take.
                - Use only if the attributes category is `category`.
                - None of the category options can exceed max 200 characters.
                For example:
                    [{“value”:1, “label”:“male”}, {“value”:2, “label”:“female”}]
            is_recurring: Type of the attribute. Use only if the attributes
                category is `calculated` or `global`
            multi_category_options: List of options you want to add for
                multiple-choice.
                - Use only if the attributes category is `normal`
                    and attributes type is `multiple-choice`.
                - None of the multicategory options can exceed max 200 characters.
                For example: [“USA”,“INDIA”]
            attribute_type: Type of the attribute.
                - Use only if the attributes category is `normal`, `category` or
                    `transactional`.
                - Type `user` and `multiple-choice` is only available if the category
                    is `normal` attribute
                - Type `id` is only available if the category is `transactional`
                    attribute.
                - Type `category` is only available if the category is
                    `category` attribute.
            value: Value of the attribute. Use only if the attributes category
                is `calculated` or `global`

        Returns: Parsed JSON Response
        """
        payload: dict[str, Any] = {}

        if attribute_type:
            payload["type"] = attribute_type
        if enumeration:
            payload["enumeration"] = enumeration
        if multi_category_options:
            payload["multiCategoryOptions"] = multi_category_options
        if is_recurring is not None:
            payload["isRecurring"] = is_recurring
        if value:
            payload["value"] = value

        return self._post(
            f"/contacts/attributes/{attribute_category}/{attribute_name}",
            payload=payload,
        )

    def delete_attribute(
        self,
        attribute_name: str,
        attribute_category: Literal[
            "normal", "transactional", "category", "calculated", "global"
        ] = "normal",
    ) -> dict[str, Any]:
        """Delete a Brevo Contact Attribute.

        Args:
            attribute_name: Name of the attribute.
            attribute_category: Category of the attribute
                Allowed values `normal`, `transactional`, `category`,
                `calculated`, `global`

        Returns: Parsed JSON Response
        """
        return self._delete(
            f"/contacts/attributes/{attribute_category}/{attribute_name}"
        )

    # endregion
