"""
Run the graph embedding methods on Karate graph and evaluate them on
graph reconstruction and visualization. Please copy the
gem/data/karate.edgelist to the working directory
"""
import pickle
import numpy as np
from time import time
import networkx as nx
import matplotlib.pyplot as plt
from argparse import ArgumentParser

from gem.evaluation import visualize_embedding as viz
from gem.evaluation import evaluate_graph_reconstruction as gr

from gem.embedding.lle import LocallyLinearEmbedding
from gem.embedding.lap import LaplacianEigenmaps
from gem.embedding.gf import GraphFactorization
from gem.embedding.node2vec import node2vec
from gem.embedding.hope import HOPE
from gem.embedding.sdne import SDNE


if __name__ == '__main__':
    ''' Sample usage
    python run_sbm.py -node2vec 1
    '''
    parser = ArgumentParser(description='Graph Embedding Experiments on SBM Graph')
    parser.add_argument('-node2vec', '--node2vec',
                        help='whether to run node2vec (default: False)')
    args = vars(parser.parse_args())
    try:
        run_n2v = bool(int(args["node2vec"]))
    except (KeyError, TypeError, ValueError):
        run_n2v = False

    # File that contains the edges. Format: source target
    # Optionally, you can add weights as third column: source target weight
    file_prefix = 'data/sbm.gpickle'
    # Specify whether the edges are directed
    isDirected = True

    # Load graph
    G = nx.read_gpickle(file_prefix)
    # convert G (networkx 1.x digraph) to networkx 2.x
    H = nx.DiGraph()
    H.add_nodes_from(G.node)
    for source_node in G.edge.keys():
        for target_node in G.edge[source_node].keys():
            H.add_edge(source_node, target_node)
    G = H
    try:
        node_colors = pickle.load(
            open('data/sbm_node_labels.pickle', 'rb')
        )
    except UnicodeDecodeError:
        node_colors = pickle.load(
            open('data/sbm_node_labels.pickle', 'rb'), encoding='latin1'
        )
    node_colors_arr = [None] * node_colors.shape[0]
    for idx in range(node_colors.shape[0]):
        node_colors_arr[idx] = np.where(node_colors[idx, :].toarray() == 1)[1][0]

    models = list()
    # Load the models you want to run
    models.append(GraphFactorization(d=128, max_iter=1000, eta=1 * 10 ** -4, regu=1.0, data_set='sbm'))
    models.append(HOPE(d=256, beta=0.01))
    models.append(LaplacianEigenmaps(d=128))
    models.append(LocallyLinearEmbedding(d=128))
    if run_n2v:
        models.append(
            node2vec(d=182, max_iter=1, walk_len=80, num_walks=10, con_size=10, ret_p=1, inout_p=1, data_set='sbm')
        )
    models.append(SDNE(d=128, beta=5, alpha=1e-5, nu1=1e-6, nu2=1e-6, K=3,n_units=[500, 300, ], rho=0.3, n_iter=30,
                       xeta=0.001,n_batch=500, modelfile=['enc_model.json', 'dec_model.json'],
                       weightfile=['enc_weights.hdf5', 'dec_weights.hdf5']))
    # For each model, learn the embedding and evaluate on graph reconstruction and visualization
    for embedding in models:
        print('Num nodes: %d, num edges: %d' % (G.number_of_nodes(), G.number_of_edges()))
        t1 = time()
        # Learn embedding - accepts a networkx graph or file with edge list
        Y = embedding.learn_embedding(graph=G, edge_f=None, is_weighted=True, no_python=True)
        print(embedding.get_method_name()+':\n\tTraining time: %f' % (time() - t1))
        # Evaluate on graph reconstruction
        MAP, prec_curv, err, err_baseline = gr.evaluateStaticGraphReconstruction(G, embedding, Y, None)
        # ---------------------------------------------------------------------------------
        print(("\tMAP: {} \t preccision curve: {}\n\n\n\n"+'-'*100).format(MAP, prec_curv[:5]))
        # ---------------------------------------------------------------------------------
        # Visualize
        viz.plot_embedding2D(embedding.get_embedding(), di_graph=G, node_colors=node_colors_arr)
        plt.title(embedding.get_method_name())
        plt.show()
        plt.clf()
