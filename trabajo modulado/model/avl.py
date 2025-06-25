import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st
class AVLNode:
    def __init__(self, key, freq):
        self.key = key
        self.freq = freq
        self.left = None
        self.right = None
        self.height = 1

class AVLTree:
    def insert(self, root, key, freq):
        if not root:
            return AVLNode(key, freq)

        if key < root.key:
            root.left = self.insert(root.left, key, freq)
        elif key > root.key:
            root.right = self.insert(root.right, key, freq)
        else:
            root.freq = freq
            return root


    # resto igual (rotaciones y balanceos)


        root.height = 1 + max(self.getHeight(root.left), self.getHeight(root.right))

        balance = self.getBalance(root)

        # Rotaciones AVL
        # Left Left
        if balance > 1 and key < root.left.key:
            return self.rightRotate(root)
        # Right Right
        if balance < -1 and key > root.right.key:
            return self.leftRotate(root)
        # Left Right
        if balance > 1 and key > root.left.key:
            root.left = self.leftRotate(root.left)
            return self.rightRotate(root)
        # Right Left
        if balance < -1 and key < root.right.key:
            root.right = self.rightRotate(root.right)
            return self.leftRotate(root)

        return root

    def leftRotate(self, z):
        y = z.right
        T2 = y.left
        y.left = z
        z.right = T2
        z.height = 1 + max(self.getHeight(z.left), self.getHeight(z.right))
        y.height = 1 + max(self.getHeight(y.left), self.getHeight(y.right))
        return y

    def rightRotate(self, z):
        y = z.left
        T3 = y.right
        y.right = z
        z.left = T3
        z.height = 1 + max(self.getHeight(z.left), self.getHeight(z.right))
        y.height = 1 + max(self.getHeight(y.left), self.getHeight(y.right))
        return y

    def getHeight(self, root):
        if not root:
            return 0
        return root.height

    def getBalance(self, root):
        if not root:
            return 0
        return self.getHeight(root.left) - self.getHeight(root.right)

    def preorder(self, root):
        res = []
        if root:
            res.append((root.key, root.freq))
            res += self.preorder(root.left)
            res += self.preorder(root.right)
        return res
    
