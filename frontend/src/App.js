import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Health Score Badge Component
const HealthBadge = ({ score, rating }) => {
  const getColor = (score) => {
    if (score >= 85) return "bg-green-500";
    if (score >= 70) return "bg-green-400";
    if (score >= 55) return "bg-yellow-500";
    if (score >= 40) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div className={`inline-flex items-center px-3 py-1 rounded-full text-white text-sm font-medium ${getColor(score)}`}>
      <span className="mr-1">{score}/100</span>
      <span>{rating}</span>
    </div>
  );
};

// Nutrition Bar Component
const NutritionBar = ({ label, value, unit, maxValue, color = "bg-blue-500" }) => {
  const percentage = maxValue ? Math.min((value / maxValue) * 100, 100) : 0;
  
  return (
    <div className="mb-2">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>{label}</span>
        <span>{value ? `${value}${unit}` : "N/A"}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div 
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );
};

// Indian Food Categories Component
const IndianFoodCategories = ({ onCategorySelect }) => {
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await axios.get(`${API}/food/categories`);
        setCategories(response.data);
      } catch (error) {
        console.error("Error fetching categories:", error);
      }
    };
    fetchCategories();
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-4">
      <h3 className="text-lg font-semibold mb-3">Popular Indian Food Categories</h3>
      <div className="flex flex-wrap gap-2">
        {categories.slice(0, 20).map((category) => (
          <button
            key={category}
            onClick={() => onCategorySelect(category)}
            className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm hover:bg-orange-200 transition-colors"
          >
            {category}
          </button>
        ))}
      </div>
    </div>
  );
};

// Popular Indian Foods Component
const PopularIndianFoods = ({ onProductSelect }) => {
  const [popularFoods, setPopularFoods] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPopularFoods = async () => {
      try {
        const response = await axios.get(`${API}/food/popular-indian`);
        setPopularFoods(response.data);
      } catch (error) {
        console.error("Error fetching popular foods:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPopularFoods();
  }, []);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-4 mb-4">
        <h3 className="text-lg font-semibold mb-3">Popular Indian Foods</h3>
        <div className="text-center py-4">Loading popular foods...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-4">
      <h3 className="text-lg font-semibold mb-3">Popular Indian Foods</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {popularFoods.map((food) => (
          <div
            key={food.id}
            onClick={() => onProductSelect(food)}
            className="cursor-pointer p-3 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
          >
            {food.image_url && (
              <img 
                src={food.image_url} 
                alt={food.product_name}
                className="w-full h-16 object-cover rounded mb-2"
              />
            )}
            <h4 className="text-sm font-medium text-gray-800 mb-1 line-clamp-2">
              {food.product_name}
            </h4>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">{food.brand}</span>
              <HealthBadge score={food.health_score} rating={food.health_rating} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Food Product Card Component
const FoodProductCard = ({ product, onTrack }) => {
  const [isTracking, setIsTracking] = useState(false);
  const [quantity, setQuantity] = useState(100);

  const handleTrack = async () => {
    setIsTracking(true);
    try {
      await onTrack(product, quantity);
    } finally {
      setIsTracking(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-4 hover:shadow-lg transition-shadow">
      <div className="flex items-start space-x-4">
        {product.image_url && (
          <img 
            src={product.image_url} 
            alt={product.product_name}
            className="w-20 h-20 object-cover rounded-lg"
          />
        )}
        <div className="flex-1">
          <div className="flex justify-between items-start mb-2">
            <div>
              <h3 className="text-lg font-semibold text-gray-800">{product.product_name}</h3>
              {product.brand && <p className="text-sm text-gray-600">{product.brand}</p>}
            </div>
            <HealthBadge score={product.health_score} rating={product.health_rating} />
          </div>
          
          {product.nutriscore_grade && (
            <div className="mb-2">
              <span className="text-sm font-medium text-gray-700">Nutri-Score: </span>
              <span className={`inline-block px-2 py-1 rounded text-white text-xs font-bold ${
                product.nutriscore_grade === 'a' ? 'bg-green-600' :
                product.nutriscore_grade === 'b' ? 'bg-green-400' :
                product.nutriscore_grade === 'c' ? 'bg-yellow-500' :
                product.nutriscore_grade === 'd' ? 'bg-orange-500' : 'bg-red-500'
              }`}>
                {product.nutriscore_grade.toUpperCase()}
              </span>
            </div>
          )}

          {product.nutrition && (
            <div className="grid grid-cols-2 gap-4 mb-4">
              <NutritionBar 
                label="Energy" 
                value={product.nutrition.energy_100g} 
                unit="kcal" 
                maxValue={500}
                color="bg-purple-500"
              />
              <NutritionBar 
                label="Sugar" 
                value={product.nutrition.sugars_100g} 
                unit="g" 
                maxValue={25}
                color="bg-red-500"
              />
              <NutritionBar 
                label="Fat" 
                value={product.nutrition.fat_100g} 
                unit="g" 
                maxValue={30}
                color="bg-yellow-500"
              />
              <NutritionBar 
                label="Protein" 
                value={product.nutrition.proteins_100g} 
                unit="g" 
                maxValue={25}
                color="bg-green-500"
              />
            </div>
          )}

          {product.additives && product.additives.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-1">Additives:</p>
              <p className="text-sm text-red-600">{product.additives.join(", ")}</p>
            </div>
          )}

          <div className="flex items-center space-x-2">
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value))}
              min="1"
              max="1000"
              className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
            />
            <span className="text-sm text-gray-600">grams</span>
            <button
              onClick={handleTrack}
              disabled={isTracking}
              className="px-4 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:bg-gray-400"
            >
              {isTracking ? "Tracking..." : "Track"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Search Component
const FoodSearch = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Search Food Products</h2>
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter food name or barcode..."
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </form>
    </div>
  );
};

// Food Tracking History Component
const FoodTrackingHistory = ({ userId }) => {
  const [trackingHistory, setTrackingHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchTrackingHistory = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API}/food/track/${userId}`);
      setTrackingHistory(response.data);
    } catch (error) {
      console.error("Error fetching tracking history:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchTrackingHistory();
    }
  }, [userId]);

  const deleteEntry = async (entryId) => {
    try {
      await axios.delete(`${API}/food/track/${entryId}`);
      setTrackingHistory(prev => prev.filter(entry => entry.id !== entryId));
    } catch (error) {
      console.error("Error deleting entry:", error);
    }
  };

  if (isLoading) {
    return <div className="text-center py-4">Loading tracking history...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Food Tracking History</h2>
      {trackingHistory.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No tracked foods yet. Start searching and tracking!</p>
      ) : (
        <div className="space-y-4">
          {trackingHistory.map((entry) => (
            <div key={entry.id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="font-medium">{entry.food_product.product_name}</h3>
                  <p className="text-sm text-gray-600">{entry.quantity}g tracked</p>
                </div>
                <div className="flex items-center space-x-2">
                  <HealthBadge score={entry.food_product.health_score} rating={entry.food_product.health_rating} />
                  <button
                    onClick={() => deleteEntry(entry.id)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <p className="text-xs text-gray-500">
                {new Date(entry.timestamp).toLocaleDateString()} at {new Date(entry.timestamp).toLocaleTimeString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Main App Component
function App() {
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [userId] = useState("user_123"); // In a real app, this would come from authentication
  const [refreshHistory, setRefreshHistory] = useState(0);

  const handleSearch = async (query) => {
    setIsSearching(true);
    try {
      const response = await axios.post(`${API}/food/search`, { query });
      setSearchResults(response.data);
    } catch (error) {
      console.error("Error searching foods:", error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleTrackFood = async (product, quantity) => {
    try {
      await axios.post(`${API}/food/track`, {
        user_id: userId,
        food_product: product,
        quantity: quantity
      });
      setRefreshHistory(prev => prev + 1);
      alert("Food tracked successfully!");
    } catch (error) {
      console.error("Error tracking food:", error);
      alert("Error tracking food. Please try again.");
    }
  };

  // Test API connection on load
  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await axios.get(`${API}/`);
        console.log("API Connection:", response.data.message);
      } catch (error) {
        console.error("API Connection Error:", error);
      }
    };
    testConnection();
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Food Health Tracker</h1>
          <p className="text-gray-600">Track your food intake and discover how healthy your choices are</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <FoodSearch onSearch={handleSearch} isLoading={isSearching} />
            
            <div className="space-y-4">
              {searchResults.length > 0 && (
                <h2 className="text-xl font-semibold text-gray-800">Search Results</h2>
              )}
              {searchResults.map((product) => (
                <FoodProductCard
                  key={product.id}
                  product={product}
                  onTrack={handleTrackFood}
                />
              ))}
            </div>
          </div>

          <div className="lg:col-span-1">
            <FoodTrackingHistory userId={userId} key={refreshHistory} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;