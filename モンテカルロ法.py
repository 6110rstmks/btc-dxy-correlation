
import numpy as np
import matplotlib.pyplot as plt
np.random.seed(42)

# シミュレーション
n_points = 10000
x = np.random.uniform(0, 1, n_points)
y = np.random.uniform(0, 1, n_points)
inside = x**2 + y**2 <= 1

# 収束の様子
n_range = np.arange(1, n_points + 1)
pi_estimates = np.cumsum(inside) / n_range * 4

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 左: 点のプロット
axes[0].scatter(x[inside], y[inside], s=1, alpha=0.5, c='steelblue', label='Inside')
axes[0].scatter(x[~inside], y[~inside], s=1, alpha=0.5, c='salmon', label='Outside')
theta = np.linspace(0, np.pi/2, 100)
axes[0].plot(np.cos(theta), np.sin(theta), 'k-', linewidth=2)
axes[0].set_aspect('equal')
axes[0].set_title(f'Monte Carlo: pi = {pi_estimates[-1]:.4f}', fontsize=13)
axes[0].legend(markerscale=10)

# 右: 収束の様子
axes[1].plot(n_range, pi_estimates, linewidth=0.8, color='steelblue')
axes[1].axhline(y=np.pi, color='red', linestyle='--', linewidth=1.5, label=f'pi={np.pi:.4f}')
axes[1].set_xlabel('Number of Samples')
axes[1].set_ylabel('Estimated pi')
axes[1].set_title('Convergence of Estimation', fontsize=13)
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()