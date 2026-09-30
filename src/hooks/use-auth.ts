export function useAuth() {
  return {
    isLoading: false,
    isAuthenticated: true,
    user: { _id: "1", name: "Guest User", email: "guest@safar.stats.gov.in" },
    signIn: async () => {},
    signOut: async () => {},
  };
}
