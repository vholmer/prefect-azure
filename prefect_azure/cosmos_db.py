"""Tasks for interacting with Azure Cosmos DB"""

from functools import partial
from typing import Any, Dict, List, Optional, Union

from anyio import to_thread
from azure.cosmos.database import ContainerProxy, DatabaseProxy
from prefect import task
from prefect.logging import get_run_logger

from prefect_azure.credentials import CosmosDbAzureCredentials


def _get_container_client(azure_credentials, container, database):
    """
    Helper to get the container client.
    """
    cosmos_db_client = azure_credentials.get_client()
    database_client = cosmos_db_client.get_database_client(database)
    container_client = database_client.get_container_client(container)
    return container_client


@task
async def cosmos_db_query_items(
    query: str,
    container: Union[str, ContainerProxy, Dict[str, Any]],
    database: Union[str, DatabaseProxy, Dict[str, Any]],
    azure_credentials: CosmosDbAzureCredentials,
    parameters: Optional[List[Dict[str, object]]] = None,
    partition_key: Optional[Any] = None,
    **kwargs: Any
) -> List[Union[str, dict]]:
    """
    Return all results matching the given query.

    You can use any value for the container name in the FROM clause,
    but often the container name is used.
    In the examples below, the container name is "products,"
    and is aliased as "p" for easier referencing in the WHERE clause.

    Args:
        query: The Azure Cosmos DB SQL query to execute.
        container: The ID (name) of the container, a ContainerProxy instance,
            or a dict representing the properties of the container to be retrieved.
        database: The ID (name), dict representing the properties
            or DatabaseProxy instance of the database to read.
        azure_credentials: Credentials to use for authentication with Azure.
        parameters: Optional array of parameters to the query.
            Each parameter is a dict() with 'name' and 'value' keys.
        partition_key: Partition key for the item to retrieve.
        **kwargs: Additional keyword arguments to pass.

    Returns:
        An `list` of results.

    Example:
        Query SampleDB Persons container where age >= 44
        ```python
        from prefect import flow

        from prefect_azure import CosmosDbAzureCredentials
        from prefect_azure.cosmos_db import cosmos_db_query_items

        @flow
        async def example_cosmos_db_query_items_flow():
            connection_string = "connection_string"
            azure_credentials = CosmosDbAzureCredentials(connection_string)

            query = "SELECT * FROM c where c.age >= @age"
            container = "Persons"
            database = "SampleDB"
            parameters = [dict(name="@age", value=44)]

            results = await cosmos_db_query_items(
                query,
                container,
                database,
                azure_credentials,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
            return results

        await example_cosmos_db_query_items_flow()
        ```
    """
    logger = get_run_logger()
    logger.info("Running query from container %s in %s database", container, database)

    container_client = _get_container_client(azure_credentials, container, database)
    query_items = partial(
        container_client.query_items, query, parameters=parameters, **kwargs
    )
    results = await to_thread.run_sync(query_items)
    return results


@task
async def cosmos_db_read_item(
    item: Union[str, Dict[str, Any]],
    partition_key: Any,
    container: Union[str, ContainerProxy, Dict[str, Any]],
    database: Union[str, DatabaseProxy, Dict[str, Any]],
    azure_credentials: CosmosDbAzureCredentials,
    **kwargs: Any
) -> List[Union[str, dict]]:
    """
    Get the item identified by item.

    Args:
        item: The ID (name) or dict representing item to retrieve.
        partition_key: Partition key for the item to retrieve.
        container: The ID (name) of the container, a ContainerProxy instance,
            or a dict representing the properties of the container to be retrieved.
        database: The ID (name), dict representing the properties
            or DatabaseProxy instance of the database to read.
        azure_credentials: Credentials to use for authentication with Azure.
        **kwargs: Additional keyword arguments to pass.

    Returns:
        Dict representing the item to be retrieved.

    Example:
        Read an item using a partition key from Cosmos DB.
        ```python
        from prefect import flow

        from prefect_azure import CosmosDbAzureCredentials
        from prefect_azure.cosmos_db import cosmos_db_read_item

        @flow
        async def example_cosmos_db_read_item_flow():
            connection_string = "connection_string"
            azure_credentials = CosmosDbAzureCredentials(connection_string)

            item = "item"
            partition_key = "partition_key"
            container = "container"
            database = "database"

            result = await cosmos_db_read_item(
                item,
                partition_key,
                container,
                database,
                azure_credentials
            )
            return result

        await example_cosmos_db_read_item_flow()
        ```
    """
    logger = get_run_logger()
    logger.info(
        "Reading item %s with partition_key %s from container %s in %s database",
        item,
        partition_key,
        container,
        database,
    )

    container_client = _get_container_client(azure_credentials, container, database)
    read_item = partial(container_client.read_item, item, partition_key, **kwargs)
    result = await to_thread.run_sync(read_item)
    return result


@task
def cosmos_db_create_item(
    body: Dict[str, Any],
    container: Union[str, ContainerProxy, Dict[str, Any]],
    database: Union[str, DatabaseProxy, Dict[str, Any]],
    azure_credentials: CosmosDbAzureCredentials,
    **kwargs: Any
) -> dict[[str, Any]]:
    """
    Create an item in the container.

    To update or replace an existing item, use the upsert_item method.

    Args:
        body: A dict-like object representing the item to create.
        container: The ID (name) of the container, a ContainerProxy instance,
            or a dict representing the properties of the container to be retrieved.
        database: The ID (name), dict representing the properties
            or DatabaseProxy instance of the database to read.
        azure_credentials: Credentials to use for authentication with Azure.
        **kwargs: Additional keyword arguments to pass.

    Returns:
        A dict representing the new item.

    Example:
        Create an item in the container.

        To update or replace an existing item, use the upsert_item method.
        ```python
        import uuid

        from prefect import flow

        from prefect_azure import CosmosDbAzureCredentials
        from prefect_azure.cosmos_db import cosmos_db_create_item


        @flow
        async def example_cosmos_db_create_item_flow():
            azure_credentials = CosmosDbAzureCredentials(connection_string)

            body = {
                "firstname": "Olivia",
                "age": 3,
                "id": str(uuid.uuid4())
            }
            container = "Persons"
            database = "SampleDB"

            result = await cosmos_db_create_item(
                body,
                container,
                database,
                azure_credentials
            )
            return result

        await example_cosmos_db_create_item_flow()
        ```
    """
    logger = get_run_logger()
    logger.info(
        "Creating the item within container %s under %s database",
        container,
        database,
    )

    container_client = _get_container_client(azure_credentials, container, database)
    create_item = partial(container_client.create_item, body, **kwargs)
    result = await to_thread.run_sync(create_item)
    return result
