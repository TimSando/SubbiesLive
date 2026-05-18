import React from 'react';

export default function ToggleSwitch({ value, onChange, options = [
  { value: 'total', label: 'Total' },
  { value: 'average', label: 'Average' }
] }) {
  return (
    <div className="toggle-switch">
      <div 
        className="toggle-switch__slider" 
        style={{ 
          transform: `translateX(${value === options[1].value ? '100%' : '0'})` 
        }} 
      />
      {options.map((option) => (
        <button
          key={option.value}
          className={`toggle-switch__option ${value === option.value ? 'toggle-switch__option--active' : ''}`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
