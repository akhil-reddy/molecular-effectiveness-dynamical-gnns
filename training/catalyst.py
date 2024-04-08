# -*- coding: utf-8 -*-
"""Catalyst.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1YDqRuDE9XnL2kbFPyHDjyaoKD0L5LEkE
"""

import pandas as pd
import torch
from rdkit import Chem
from torch_geometric.data import Data, Batch
import networkx as nx
import matplotlib.pyplot as plt
from torch_geometric.utils import to_networkx


# Load the CSV dataset
data = pd.read_csv('data/catalyst.csv')
print(data.shape)

def molecule_to_graph(molecule):
    num_atoms = molecule.GetNumAtoms()
    x = torch.tensor([atom_feature_vector(atom) for atom in molecule.GetAtoms()], dtype=torch.float)
    edge_index = []
    edge_attr = []
    for bond in molecule.GetBonds():
        edge_index.extend([[bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()], [bond.GetEndAtomIdx(), bond.GetBeginAtomIdx()]])
        edge_attr.extend([bond_feature_vector(bond), bond_feature_vector(bond)])
    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
    edge_attr = torch.tensor(edge_attr, dtype=torch.float)
    return Data(x=x, edge_index=edge_index, edge_attr=edge_attr)

def atom_feature_vector(atom):
    return [atom.GetAtomicNum(), atom.GetDegree(), atom.GetHybridization()]

def bond_feature_vector(bond):
    return [bond.GetBondTypeAsDouble(), bond.IsInRing()]

def visualize(graph):
    nx_graph = to_networkx(graph, to_undirected=True)

    fig = plt.figure(figsize=(10, 10))
    pos = nx.spring_layout(nx_graph)

    nx.draw_networkx(nx_graph, pos, with_labels=True, node_size=500, font_size=12, font_weight='bold')

    if 'edge_attr' in next(iter(nx_graph.edges(data=True)))[-1]:
        edge_labels = {(u, v): d['edge_attr'] for u, v, d in nx_graph.edges(data=True)}
        nx.draw_networkx_edge_labels(nx_graph, pos, edge_labels=edge_labels, font_size=10)

    plt.axis('off')
    plt.show()

# Process each row of the dataset
graphs = []
for _, row in data.iterrows():
    # Convert SMILES to molecule objects
    molecule1 = Chem.MolFromSmiles(row['Drug1'])
    molecule2 = Chem.MolFromSmiles(row['Drug2'])

    # Convert molecules to graph representations
    graph1 = molecule_to_graph(molecule1)
    graph2 = molecule_to_graph(molecule2)

    # Create the "Catalyst Score" node
    catalyst_score_features = torch.tensor([[
        row['CSS'],
        row['Synergy_ZIP'],
        row['Synergy_Bliss'],
        row['Synergy_Loewe'],
        row['Synergy_HSA'],
        row['Y']
    ]], dtype=torch.float)
    catalyst_score_node_index = graph1.x.shape[0] + graph2.x.shape[0]

    # Pad the node features of graph1 and graph2 to match the size of the "Catalyst Score" node features
    pad_size = catalyst_score_features.shape[1] - graph1.x.shape[1]
    graph1_x_padded = torch.cat([graph1.x, torch.zeros((graph1.x.shape[0], pad_size))], dim=1)
    graph2_x_padded = torch.cat([graph2.x, torch.zeros((graph2.x.shape[0], pad_size))], dim=1)

    # Combine the padded node features of graph1, graph2, and the "Catalyst Score" node
    combined_x = torch.cat([graph1_x_padded, graph2_x_padded, catalyst_score_features])

    graph1_edge_index = torch.cat([
    torch.tensor([[i, catalyst_score_node_index] for i in range(graph1.x.shape[0])]),
    torch.tensor([[catalyst_score_node_index, i] for i in range(graph1.x.shape[0])])
    ], dim=0).t().contiguous()
    graph1_edge_attr = torch.ones((graph1_edge_index.shape[1], graph1.edge_attr.shape[1]), dtype=torch.float)

    # Create edges between each node in graph2 and the "Catalyst Score" node
    graph2_edge_index = torch.cat([
        torch.tensor([[i + graph1.x.shape[0], catalyst_score_node_index] for i in range(graph2.x.shape[0])]),
        torch.tensor([[catalyst_score_node_index, i + graph1.x.shape[0]] for i in range(graph2.x.shape[0])])
    ], dim=0).t().contiguous()
    graph2_edge_attr = torch.ones((graph2_edge_index.shape[1], graph2.edge_attr.shape[1]), dtype=torch.float)

    # Combine the edge indices and attributes
    combined_edge_index = torch.cat([graph1.edge_index, graph2.edge_index + graph1.x.shape[0], graph1_edge_index, graph2_edge_index], dim=1)
    combined_edge_attr = torch.cat([graph1.edge_attr, graph2.edge_attr, graph1_edge_attr, graph2_edge_attr], dim=0)

    # Create the combined graph
    combined_graph = Data(x=combined_x, edge_index=combined_edge_index, edge_attr=combined_edge_attr)
    graphs.append(combined_graph)

print(len(graphs))