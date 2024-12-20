from blarify.project_graph_creator import ProjectGraphCreator
from blarify.project_file_explorer import ProjectFilesIterator
from blarify.project_graph_updater import ProjectGraphUpdater
from blarify.project_graph_diff_creator import ProjectGraphDiffCreator
from blarify.db_managers.neo4j_manager import Neo4jManager
from blarify.code_references import LspQueryHelper
from blarify.graph.graph_environment import GraphEnvironment
from blarify.utils.file_remover import FileRemover
import time
import dotenv
import os


def main(root_path: str = None, blarignore_path: str = None):
    lsp_query_helper = LspQueryHelper(root_uri=root_path)

    lsp_query_helper.start()

    project_files_iterator = ProjectFilesIterator(
        root_path=root_path,
        blarignore_path=blarignore_path,
    )

    FileRemover.soft_delete_if_exists(root_path, "Gemfile")

    repoId = "test-ruby"
    entity_id = "test"
    graph_manager = Neo4jManager(repoId, entity_id)

    graph_creator = ProjectGraphCreator(
        "Test", lsp_query_helper, project_files_iterator, GraphEnvironment("dev", "MAIN", root_path)
    )

    graph = graph_creator.build()

    relationships = graph.get_relationships_as_objects()
    nodes = graph.get_nodes_as_objects()

    print(f"Saving graph with {len(nodes)} nodes and {len(relationships)} relationships")
    # graph_manager.save_graph(nodes, relationships)
    graph_manager.close()

    lsp_query_helper.shutdown_exit_close()


def main_diff(file_diffs: list, root_uri: str = None, blarignore_path: str = None):
    lsp_query_helper = LspQueryHelper(root_uri=root_uri)
    lsp_query_helper.start()

    project_files_iterator = ProjectFilesIterator(
        root_path=root_uri,
        blarignore_path=blarignore_path,
    )

    repoId = "test"
    entity_id = "test"
    graph_manager = Neo4jManager(repoId, entity_id)

    graph_diff_creator = ProjectGraphDiffCreator(
        root_path=root_uri,
        lsp_query_helper=lsp_query_helper,
        project_files_iterator=project_files_iterator,
        file_diffs=file_diffs,
        graph_environment=GraphEnvironment("dev", "MAIN", root_uri),
        pr_environment=GraphEnvironment("dev", "pr-123", root_uri),
    )

    graph = graph_diff_creator.build()

    relationships = graph.get_relationships_as_objects()
    nodes = graph.get_nodes_as_objects()

    print(f"Saving graph with {len(nodes)} nodes and {len(relationships)} relationships")
    graph_manager.save_graph(nodes, relationships)
    graph_manager.close()
    lsp_query_helper.shutdown_exit_close()


def main_update(updated_files: list, root_uri: str = None, blarignore_path: str = None):
    lsp_query_helper = LspQueryHelper(root_uri=root_uri)
    lsp_query_helper.start()

    project_files_iterator = ProjectFilesIterator(
        root_path=root_uri,
        blarignore_path=blarignore_path,
    )

    repoId = "test"
    entity_id = "test"
    graph_manager = Neo4jManager(repoId, entity_id)

    delete_updated_files_from_neo4j(updated_files, graph_manager)

    graph_diff_creator = ProjectGraphUpdater(
        updated_files=updated_files,
        root_path=root_uri,
        lsp_query_helper=lsp_query_helper,
        project_files_iterator=project_files_iterator,
        graph_environment=GraphEnvironment("dev", "MAIN", root_uri),
    )

    graph = graph_diff_creator.build()

    relationships = graph.get_relationships_as_objects()
    nodes = graph.get_nodes_as_objects()

    print(f"Saving graph with {len(nodes)} nodes and {len(relationships)} relationships")
    graph_manager.save_graph(nodes, relationships)
    graph_manager.close()
    lsp_query_helper.shutdown_exit_close()


def delete_updated_files_from_neo4j(updated_files, db_manager: Neo4jManager):
    for updated_file in updated_files:
        db_manager.detatch_delete_nodes_with_path(updated_file.path)


if __name__ == "__main__":
    dotenv.load_dotenv()
    root_path = "/Users/berrazuriz/Desktop/Blar/repositories/blar-django-server/"
    blarignore_path = os.getenv("BLARIGNORE_PATH")

    start_time = time.time()
    main(
        root_path=root_path,
        blarignore_path=blarignore_path,
    )
    end_time = time.time()

    print(f"Execution time: {end_time - start_time} seconds")
