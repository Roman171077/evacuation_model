import numpy as np
import matplotlib.pyplot as plt

print("NumPy version:", np.__version__)

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.plot(x, y)
plt.title("Test plot")
plt.show()