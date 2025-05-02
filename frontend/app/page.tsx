import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { UserButton } from '@clerk/nextjs'

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-hibiscus-500">Hibiscus</span>
            <span className="text-md">Agent Registry</span>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <Link href="/agents" className="text-sm font-medium hover:text-hibiscus-500 transition-colors">
              Browse Agents
            </Link>
            <Link href="/register" className="text-sm font-medium hover:text-hibiscus-500 transition-colors">
              Register Agent
            </Link>
            <Link href="/dashboard" className="text-sm font-medium hover:text-hibiscus-500 transition-colors">
              Dashboard
            </Link>
          </nav>
          <div className="flex items-center gap-4">
            <UserButton afterSignOutUrl="/" />
          </div>
        </div>
      </header>
      <main className="flex-1">
        <section className="py-20 md:py-32 bg-gradient-to-b from-white to-gray-50 dark:from-gray-900 dark:to-gray-950">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Welcome to the <span className="text-hibiscus-500">Hibiscus</span> Agent Registry
            </h1>
            <p className="text-xl md:text-2xl text-gray-600 dark:text-gray-400 mb-12 max-w-3xl mx-auto">
              Discover, share, and connect AI agents in our federated registry platform.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild size="lg" className="bg-hibiscus-500 hover:bg-hibiscus-600">
                <Link href="/agents">Browse Agents</Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/register">Register Your Agent</Link>
              </Button>
            </div>
          </div>
        </section>
        
        <section className="py-16 bg-white dark:bg-gray-900">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center mb-12">Key Features</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-4">Agent Discovery</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Browse and search for AI agents across our federated network of registries.
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-4">Secure API Access</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Generate personal access tokens to interact with our registry programmatically.
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-4">Federation Support</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Connect with other agent registries to expand your agent ecosystem.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
      <footer className="border-t py-6 bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              © {new Date().getFullYear()} Hibiscus Agent Registry. All rights reserved.
            </p>
            <div className="flex items-center gap-4 mt-4 md:mt-0">
              <Link href="/about" className="text-sm text-gray-600 dark:text-gray-400 hover:text-hibiscus-500 transition-colors">
                About
              </Link>
              <Link href="/terms" className="text-sm text-gray-600 dark:text-gray-400 hover:text-hibiscus-500 transition-colors">
                Terms
              </Link>
              <Link href="/privacy" className="text-sm text-gray-600 dark:text-gray-400 hover:text-hibiscus-500 transition-colors">
                Privacy
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
