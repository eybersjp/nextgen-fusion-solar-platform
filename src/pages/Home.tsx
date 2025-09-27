import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui';
import { ArrowRight, Zap, Shield, Globe, TrendingUp } from 'lucide-react';

export default function Home() {
  const features = [
    {
      icon: Zap,
      title: 'Advanced Design Tools',
      description: 'AI-powered solar system design with real-time optimization and performance modeling.'
    },
    {
      icon: Shield,
      title: 'Global Compliance',
      description: 'Built-in compliance packs for international standards and local regulations.'
    },
    {
      icon: Globe,
      title: 'Multi-Currency Support',
      description: 'Support for ZAR, AUD, and USD with automatic currency conversion.'
    },
    {
      icon: TrendingUp,
      title: 'Bankability Focus',
      description: 'Generate bankable reports and documentation for project financing.'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            NextGen Fusion
            <span className="text-blue-600"> Commercial Solar</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            The world's most advanced commercial solar platform. Design, analyze, and deploy 
            solar projects with AI-powered tools and global compliance built-in.
          </p>
          <div className="flex gap-4 justify-center">
            <Link 
              to="/projects" 
              className="bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              Get Started
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link 
              to="/" 
              className="border border-gray-300 text-gray-700 px-8 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
            >
              View Dashboard
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card key={index} className="text-center hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="mx-auto w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-6 h-6 text-blue-600" />
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{feature.description}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Stats Section */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-16">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
            Trusted by Solar Professionals Worldwide
          </h2>
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-blue-600 mb-2">500+</div>
              <div className="text-gray-600">Projects Designed</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-green-600 mb-2">250MW</div>
              <div className="text-gray-600">Total Capacity</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-purple-600 mb-2">15+</div>
              <div className="text-gray-600">Countries Supported</div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Ready to Transform Your Solar Business?
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            Join the next generation of solar professionals using AI-powered design tools.
          </p>
          <Link 
            to="/projects" 
            className="bg-gradient-to-r from-blue-600 to-green-600 text-white px-12 py-4 rounded-lg font-semibold hover:from-blue-700 hover:to-green-700 transition-all transform hover:scale-105 inline-flex items-center gap-2"
          >
            Start Your First Project
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </div>
    </div>
  );
}